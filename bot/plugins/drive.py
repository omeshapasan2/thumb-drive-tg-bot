"""
Google Drive commands — configure rclone remote/path, list files, and start processing.
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

from bot.config import Config
from bot.queue_manager import video_queue, VideoTask, QueueState
from bot.processor import list_remote_files, processing_loop, format_file_size
from bot.ram_monitor import get_ram_usage, log_ram_status

logger = logging.getLogger(__name__)

# Per-user settings (in-memory; for production, use a database)
user_settings: dict[int, dict] = {}


def get_user_settings(user_id: int) -> dict:
    """Get or create user settings."""
    if user_id not in user_settings:
        user_settings[user_id] = {
            "remote": Config.RCLONE_REMOTE,
            "path": Config.RCLONE_PATH,
        }
    return user_settings[user_id]


@Client.on_message(filters.command("set_remote") & filters.private)
async def set_remote_command(client: Client, message: Message):
    """Set the rclone remote name."""
    if not Config.is_authorized(message.from_user.id):
        await message.reply_text("⛔ You are not authorized to use this bot.", quote=True)
        return

    if len(message.command) < 2:
        settings = get_user_settings(message.from_user.id)
        await message.reply_text(
            f"**Current rclone remote:** `{settings['remote']}`\n\n"
            f"Usage: `/set_remote <name>`\n"
            f"Example: `/set_remote gdrive`",
            quote=True,
        )
        return

    remote_name = message.command[1].strip()
    settings = get_user_settings(message.from_user.id)
    settings["remote"] = remote_name

    await message.reply_text(
        f"✅ Rclone remote set to: `{remote_name}`\n\n"
        f"Now set your drive path with `/set_path <path>`",
        quote=True,
    )
    logger.info("User %d set remote to: %s", message.from_user.id, remote_name)


@Client.on_message(filters.command("set_path") & filters.private)
async def set_path_command(client: Client, message: Message):
    """Set the Google Drive directory path."""
    if not Config.is_authorized(message.from_user.id):
        await message.reply_text("⛔ You are not authorized to use this bot.", quote=True)
        return

    if len(message.command) < 2:
        settings = get_user_settings(message.from_user.id)
        await message.reply_text(
            f"**Current drive path:** `{settings['path']}`\n\n"
            f"Usage: `/set_path <path>`\n"
            f"Example: `/set_path /Movies/2024`",
            quote=True,
        )
        return

    drive_path = " ".join(message.command[1:]).strip()
    settings = get_user_settings(message.from_user.id)
    settings["path"] = drive_path

    await message.reply_text(
        f"✅ Drive path set to: `{drive_path}`\n\n"
        f"Send `/process` to start processing videos from this folder.",
        quote=True,
    )
    logger.info("User %d set path to: %s", message.from_user.id, drive_path)


@Client.on_message(filters.command("process") & filters.private)
async def process_command(client: Client, message: Message):
    """List files in the configured path and start processing."""
    if not Config.is_authorized(message.from_user.id):
        await message.reply_text("⛔ You are not authorized to use this bot.", quote=True)
        return

    if video_queue.is_running:
        await message.reply_text(
            "⚠️ Processing is already in progress!\n"
            "Use `/status` to check progress or `/cancel` to stop.",
            quote=True,
        )
        return

    settings = get_user_settings(message.from_user.id)
    remote = settings["remote"]
    path = settings["path"]

    status_msg = await message.reply_text(
        f"🔍 Scanning `{remote}:{path}` for video files...",
        quote=True,
    )

    try:
        files = await list_remote_files(remote, path)
    except Exception as e:
        await status_msg.edit_text(
            f"❌ **Failed to list files:**\n`{str(e)[:500]}`\n\n"
            f"Make sure your rclone remote `{remote}` is configured correctly."
        )
        return

    if not files:
        await status_msg.edit_text(
            f"📭 No video files found in `{remote}:{path}`\n\n"
            f"Supported formats: {', '.join(sorted(Config.VIDEO_EXTENSIONS))}"
        )
        return

    # Build the file list message
    total_size = sum(f["size"] for f in files)
    file_list = "\n".join(
        f"  {i+1}. `{f['name']}` — {format_file_size(f['size'])}"
        for i, f in enumerate(files)
    )

    await status_msg.edit_text(
        f"📁 **Found {len(files)} video(s)** in `{remote}:{path}`\n"
        f"📦 **Total size:** {format_file_size(total_size)}\n\n"
        f"{file_list}\n\n"
        f"⏳ Starting processing... Videos will be handled one at a time."
    )

    # Reset and populate the queue
    video_queue.reset()
    video_queue._is_running = True

    tasks = [
        VideoTask(
            filename=f["name"],
            remote_path=f["path"],
            file_size=f["size"],
            file_size_human=format_file_size(f["size"]),
        )
        for f in files
    ]
    await video_queue.add_tasks(tasks)

    # Start the processing loop in the background
    asyncio.create_task(
        _run_processing(client, message.chat.id, len(files))
    )


async def _run_processing(client: Client, chat_id: int, total_files: int):
    """Background task to run the processing loop and send completion message."""
    try:
        await processing_loop(client, chat_id)

        # Send completion summary
        status = video_queue.get_full_status()
        completed = len([
            t for t in video_queue.completed_list
            if t.status.value == "completed"
        ])
        failed = len([
            t for t in video_queue.completed_list
            if t.status.value == "failed"
        ])

        summary = (
            f"✅ **Processing Complete!**\n\n"
            f"📊 **Results:**\n"
            f"  ✅ Completed: {completed}/{total_files}\n"
        )
        if failed:
            summary += f"  ❌ Failed: {failed}/{total_files}\n"

            # List failed files
            failed_files = [
                t for t in video_queue.completed_list
                if t.status.value == "failed"
            ]
            for t in failed_files:
                summary += f"    • `{t.filename}`: {t.error[:100]}\n"

        await client.send_message(chat_id=chat_id, text=summary)

    except Exception as e:
        logger.error("Processing loop error: %s", e, exc_info=True)
        await client.send_message(
            chat_id=chat_id,
            text=f"❌ **Processing stopped due to error:**\n`{str(e)[:500]}`",
        )
    finally:
        video_queue._is_running = False


@Client.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: Message):
    """Show current processing status."""
    if not Config.is_authorized(message.from_user.id):
        await message.reply_text("⛔ You are not authorized.", quote=True)
        return

    state = video_queue.get_full_status()
    ram = get_ram_usage()

    text = (
        f"📊 **Processing Status**\n\n"
        f"**State:** `{state['state']}`\n"
        f"**Overall Progress:** {state['processed_count']}/{state['total_videos']} "
        f"({state['progress_percent']}%)\n"
    )

    if state["current_task"]:
        ct = state["current_task"]
        text += (
            f"\n🎬 **Currently Processing:**\n"
            f"  📄 `{ct['filename']}`\n"
            f"  📦 Size: {ct['file_size_human']}\n"
            f"  🔄 Status: `{ct['status']}`\n"
            f"  📈 Progress: `{ct['progress']:.1f}%`\n"
        )

    if state["pending"]:
        text += f"\n📋 **Queue ({len(state['pending'])} remaining):**\n"
        for i, task in enumerate(state["pending"][:10]):
            text += f"  {i+1}. `{task['filename']}` ({task['file_size_human']})\n"
        if len(state["pending"]) > 10:
            text += f"  ... and {len(state['pending']) - 10} more\n"

    text += (
        f"\n💾 **RAM:** {ram['percent']}% used "
        f"({ram['available_mb']:.0f} MB available)"
    )

    await message.reply_text(text=text, quote=True)


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_command(client: Client, message: Message):
    """Cancel current processing and clear the queue."""
    if not Config.is_authorized(message.from_user.id):
        await message.reply_text("⛔ You are not authorized.", quote=True)
        return

    if not video_queue.is_running:
        await message.reply_text("ℹ️ No processing is currently active.", quote=True)
        return

    await video_queue.cancel_all()
    await message.reply_text(
        "🛑 **Processing cancelled.** Queue has been cleared.\n\n"
        "Send `/process` to start a new batch.",
        quote=True,
    )
    logger.info("User %d cancelled processing", message.from_user.id)


@Client.on_message(filters.command("ram") & filters.private)
async def ram_command(client: Client, message: Message):
    """Show current RAM usage."""
    if not Config.is_authorized(message.from_user.id):
        await message.reply_text("⛔ You are not authorized.", quote=True)
        return

    ram = log_ram_status()

    bar_length = 20
    filled = int(bar_length * ram["percent"] / 100)
    bar = "█" * filled + "░" * (bar_length - filled)

    status_emoji = "🟢" if ram["status"] == "OK" else ("🟡" if ram["status"] == "HIGH" else "🔴")

    await message.reply_text(
        f"💾 **RAM Monitor** {status_emoji}\n\n"
        f"`[{bar}]` {ram['percent']}%\n\n"
        f"**Used:** {ram['used_mb']:.0f} MB\n"
        f"**Available:** {ram['available_mb']:.0f} MB\n"
        f"**Total:** {ram['total_mb']:.0f} MB\n\n"
        f"**Threshold:** {Config.RAM_THRESHOLD_PERCENT}% (pause)\n"
        f"**Critical:** {Config.RAM_CRITICAL_PERCENT}% (emergency cleanup)",
        quote=True,
    )
