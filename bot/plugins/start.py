"""
Start & Help commands — bot greeting and usage instructions.
Includes the Web App button for opening the Mini App dashboard.
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

from bot.config import Config

logger = logging.getLogger(__name__)

HELP_TEXT = """
🎬 **Video Thumbnail Generator Bot**

I process videos from your Google Drive, generate thumbnails, and upload everything to Telegram.

**Commands:**
• `/start` — Start the bot / show this message
• `/help` — Show detailed help
• `/set_remote <name>` — Set your rclone remote name (default: `gdrive`)
• `/set_path <path>` — Set the Google Drive folder path
• `/process` — Start processing videos from the configured path
• `/status` — Show current processing status
• `/cancel` — Cancel current processing and clear the queue
• `/ram` — Show current RAM usage stats

**How it works:**
1️⃣ Configure your rclone remote and drive path
2️⃣ Send `/process` to start
3️⃣ Videos are processed one-by-one:
   📥 Download → 📸 3 Thumbnails → 📤 Upload → 🗑️ Cleanup
4️⃣ Open the **Dashboard** to monitor progress in real-time!

⚠️ Make sure `rclone` is configured with your Google Drive credentials.
"""


@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command — greeting with Web App button."""
    user = message.from_user
    logger.info("User %s (%d) started the bot", user.first_name, user.id)

    keyboard = []

    # Web App Dashboard button (if WEBAPP_URL is configured)
    if Config.WEBAPP_URL and Config.WEBAPP_URL != "https://your-domain.com":
        keyboard.append([
            InlineKeyboardButton(
                "📊 Open Dashboard",
                web_app=WebAppInfo(url=Config.WEBAPP_URL),
            )
        ])

    keyboard.extend([
        [
            InlineKeyboardButton("📖 Help", callback_data="show_help"),
            InlineKeyboardButton("⚙️ Status", callback_data="show_status"),
        ],
    ])

    await message.reply_text(
        text=(
            f"👋 Hi **{user.first_name}**!\n\n"
            f"I'm the **Video Thumbnail Generator Bot**.\n\n"
            f"I can process videos from your Google Drive, generate "
            f"**3 evenly-spaced thumbnails** from each video, and upload "
            f"everything back to Telegram — even large files!\n\n"
            f"Use /help to see all available commands."
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        quote=True,
    )


@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Handle /help command — show usage instructions."""
    await message.reply_text(
        text=HELP_TEXT,
        quote=True,
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex("^show_help$"))
async def help_callback(client, callback_query):
    """Handle help button press."""
    await callback_query.answer()
    await callback_query.message.reply_text(
        text=HELP_TEXT,
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex("^show_status$"))
async def status_callback(client, callback_query):
    """Handle status button press."""
    from bot.queue_manager import video_queue
    from bot.ram_monitor import get_ram_usage

    await callback_query.answer()

    state = video_queue.get_full_status()
    ram = get_ram_usage()

    status_text = (
        f"📊 **Queue Status**\n\n"
        f"**State:** `{state['state']}`\n"
        f"**Progress:** {state['processed_count']}/{state['total_videos']} "
        f"({state['progress_percent']}%)\n\n"
        f"💾 **RAM:** {ram['percent']}% used "
        f"({ram['available_mb']:.0f} MB free)\n"
    )

    if state["current_task"]:
        ct = state["current_task"]
        status_text += (
            f"\n🎬 **Currently processing:**\n"
            f"  `{ct['filename']}`\n"
            f"  Status: `{ct['status']}` | Progress: `{ct['progress']:.1f}%`\n"
        )

    if state["pending"]:
        status_text += f"\n📋 **Pending:** {len(state['pending'])} videos\n"

    await callback_query.message.reply_text(text=status_text)
