"""
Video Processor — the core pipeline for video processing.

Pipeline: Download via rclone → Generate 3 thumbnails via ffmpeg → Upload to Telegram → Cleanup

All file paths use pathlib.Path with absolute resolution.
"""

import asyncio
import logging
import shlex
import shutil
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .queue_manager import video_queue, VideoTask, VideoStatus, QueueState
from .ram_monitor import check_ram, emergency_cleanup

logger = logging.getLogger(__name__)


def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"


async def run_subprocess(cmd: str, cwd: Optional[Path] = None) -> tuple[str, str, int]:
    """
    Run a shell command asynchronously.
    Returns (stdout, stderr, return_code).
    """
    logger.debug("Running: %s", cmd)
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
    )
    stdout, stderr = await process.communicate()
    return (
        stdout.decode("utf-8", errors="replace").strip(),
        stderr.decode("utf-8", errors="replace").strip(),
        process.returncode or 0,
    )


async def list_remote_files(remote: str, path: str) -> list[dict]:
    """
    List video files in the specified rclone remote path.
    Returns a list of dicts with 'name', 'size', 'path' keys.
    """
    remote_path = f"{remote}:{path}"
    cmd = f"rclone lsjson {shlex.quote(remote_path)} --fast-list --no-modtime --no-mimetype"
    stdout, stderr, rc = await run_subprocess(cmd)

    if rc != 0:
        logger.error("rclone lsjson failed: %s", stderr)
        raise RuntimeError(f"Failed to list files: {stderr}")

    import json
    try:
        files = json.loads(stdout)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse rclone output: %s", e)
        raise RuntimeError(f"Failed to parse rclone output: {e}")

    video_files = []
    for f in files:
        if f.get("IsDir", False):
            continue
        name = f.get("Name", "")
        ext = Path(name).suffix.lower()
        if ext in Config.VIDEO_EXTENSIONS:
            video_files.append({
                "name": name,
                "size": f.get("Size", 0),
                "path": f"{path}/{name}".replace("//", "/"),
            })

    # Sort by file size descending (largest first -> smallest last)
    video_files.sort(key=lambda x: x["size"], reverse=True)
    return video_files


async def download_video(task: VideoTask) -> Path:
    """
    Download a single video from Google Drive via rclone copy.
    Returns the absolute path to the downloaded file.
    """
    await video_queue.update_task_status(VideoStatus.DOWNLOADING, progress=0.0)

    # Ensure download directory exists
    Config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    remote_file = f"{Config.RCLONE_REMOTE}:{task.remote_path}"
    dest_dir = Config.DOWNLOAD_DIR.resolve()

    # Use rclone copy to download the single file
    cmd = (
        f"rclone copy {shlex.quote(remote_file)} {shlex.quote(str(dest_dir))} "
        f"--progress --stats-one-line --stats 2s"
    )

    logger.info("Downloading: %s -> %s", remote_file, dest_dir)

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Monitor download progress from stderr (rclone outputs progress there)
    while True:
        if video_queue.is_cancelled():
            process.kill()
            raise asyncio.CancelledError("Download cancelled")

        line = await process.stderr.readline()
        if not line:
            break

        line_str = line.decode("utf-8", errors="replace").strip()
        if line_str:
            # Try to parse progress percentage from rclone output
            # rclone progress looks like: "Transferred: ... 45%, ..."
            if "%" in line_str:
                try:
                    parts = line_str.split("%")
                    for part in parts:
                        nums = part.strip().split()
                        if nums:
                            last = nums[-1].rstrip(",")
                            pct = float(last)
                            if 0 <= pct <= 100:
                                await video_queue.update_task_status(
                                    VideoStatus.DOWNLOADING, progress=pct
                                )
                                break
                except (ValueError, IndexError):
                    pass

    await process.wait()

    if process.returncode != 0:
        stdout_data = await process.stdout.read()
        raise RuntimeError(
            f"rclone download failed (rc={process.returncode}): "
            f"{stdout_data.decode('utf-8', errors='replace')}"
        )

    local_file = dest_dir / task.filename
    if not local_file.exists():
        raise FileNotFoundError(f"Downloaded file not found: {local_file}")

    await video_queue.update_task_status(VideoStatus.DOWNLOADING, progress=100.0)
    logger.info("Download complete: %s (%s)", local_file, format_file_size(local_file.stat().st_size))
    return local_file.resolve()


async def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = (
        f"ffprobe -v error -show_entries format=duration "
        f"-of csv=p=0:s=x -select_streams v:0 "
        f"{shlex.quote(str(video_path))}"
    )
    stdout, stderr, rc = await run_subprocess(cmd)

    if rc != 0 or not stdout:
        logger.warning("ffprobe failed for duration, trying alternative: %s", stderr)
        # Fallback: try without stream selection
        cmd_alt = (
            f"ffprobe -v error -show_entries format=duration "
            f"-of default=noprint_wrappers=1:nokey=1 "
            f"{shlex.quote(str(video_path))}"
        )
        stdout, stderr, rc = await run_subprocess(cmd_alt)
        if rc != 0 or not stdout:
            raise RuntimeError(f"Cannot determine video duration: {stderr}")

    return float(stdout.split("x")[0].strip())


async def generate_thumbnails(video_path: Path) -> list[Path]:
    """
    Generate exactly 3 evenly-spaced screenshot thumbnails from the video.
    Returns a list of 3 absolute Path objects to the generated images.
    """
    await video_queue.update_task_status(VideoStatus.GENERATING_THUMBNAILS, progress=0.0)

    # Check RAM before ffmpeg operations
    if not check_ram():
        logger.warning("RAM threshold exceeded before thumbnail generation")
        await video_queue.set_state(QueueState.PAUSED_RAM)
        # Wait until RAM is available
        while not check_ram():
            if video_queue.is_cancelled():
                raise asyncio.CancelledError("Cancelled while waiting for RAM")
            emergency_cleanup(Config.THUMBNAIL_DIR)
            await asyncio.sleep(5)
        await video_queue.set_state(QueueState.PROCESSING)

    # Get video duration
    duration = await get_video_duration(video_path)
    logger.info("Video duration: %.2f seconds", duration)

    # Calculate 3 evenly spaced timestamps
    # Place them at 25%, 50%, and 75% of the video
    timestamps = [
        duration * 0.25,
        duration * 0.50,
        duration * 0.75,
    ]

    # Create thumbnail output directory
    thumb_dir = Config.THUMBNAIL_DIR / video_path.stem
    thumb_dir.mkdir(parents=True, exist_ok=True)

    thumbnail_paths: list[Path] = []

    for i, ts in enumerate(timestamps):
        if video_queue.is_cancelled():
            raise asyncio.CancelledError("Thumbnail generation cancelled")

        thumb_file = (thumb_dir / f"thumb_{i + 1}.jpg").resolve()
        ts_seconds = int(ts)

        # ffmpeg command: seek to timestamp, extract 1 frame, scale to 1280px width
        cmd = (
            f"ffmpeg -hide_banner -ss {ts_seconds} "
            f"-i {shlex.quote(str(video_path))} "
            f"-vf \"scale=1280:-2\" "
            f"-vframes 1 -q:v 2 -y "
            f"{shlex.quote(str(thumb_file))}"
        )

        stdout, stderr, rc = await run_subprocess(cmd)

        if thumb_file.exists() and thumb_file.stat().st_size > 0:
            thumbnail_paths.append(thumb_file)
            logger.info("Generated thumbnail %d/3: %s", i + 1, thumb_file.name)
        else:
            logger.warning(
                "Failed to generate thumbnail at %.1fs: %s", ts, stderr[:200]
            )

        # Update progress: each thumbnail is ~33%
        progress = ((i + 1) / 3) * 100
        await video_queue.update_task_status(
            VideoStatus.GENERATING_THUMBNAILS, progress=progress
        )

    if not thumbnail_paths:
        raise RuntimeError("Failed to generate any thumbnails")

    return thumbnail_paths


async def upload_to_telegram(
    bot_client,
    chat_id: int,
    video_path: Path,
    thumbnail_paths: list[Path],
) -> None:
    """
    Upload the video and its thumbnails to Telegram.
    Sends the video first, then replies with thumbnails as a media group.
    """
    from pyrogram.types import InputMediaPhoto

    await video_queue.update_task_status(VideoStatus.UPLOADING, progress=0.0)

    # Generate a small thumbnail for the video message itself
    video_thumb = Config.THUMBNAIL_DIR / f"{video_path.stem}_video_thumb.jpg"
    cmd = (
        f"ffmpeg -hide_banner -ss 1 "
        f"-i {shlex.quote(str(video_path))} "
        f"-vf \"scale=320:-2\" "
        f"-vframes 1 -q:v 5 -y "
        f"{shlex.quote(str(video_thumb))}"
    )
    await run_subprocess(cmd)

    # Get video duration for metadata
    try:
        duration = int(await get_video_duration(video_path))
    except Exception:
        duration = 0

    # Send the video file
    logger.info("Uploading video: %s", video_path.name)
    thumb_arg = str(video_thumb) if video_thumb.exists() else None

    last_update_time = [0.0]
    last_pct = [-1.0]

    async def upload_progress(current: int, total: int):
        if total == 0:
            return
        now = time.time()
        pct = min(round((current / total) * 100, 1), 99.0)
        if now - last_update_time[0] >= 1.0 or pct == 99.0 or abs(pct - last_pct[0]) >= 2.0:
            last_update_time[0] = now
            last_pct[0] = pct
            await video_queue.update_task_status(VideoStatus.UPLOADING, progress=pct)

    video_msg = await bot_client.send_video(
        chat_id=chat_id,
        video=str(video_path),
        caption=f"📹 **{video_path.name}**\n📦 Size: {format_file_size(video_path.stat().st_size)}",
        duration=duration,
        thumb=thumb_arg,
        supports_streaming=True,
        progress=upload_progress,
    )

    await video_queue.update_task_status(VideoStatus.UPLOADING, progress=99.0)

    # Send thumbnails as a media group (reply to the video)
    if thumbnail_paths:
        media_group = []
        for i, thumb_path in enumerate(thumbnail_paths):
            caption = f"📸 Screenshot {i + 1}/3" if i == 0 else ""
            media_group.append(
                InputMediaPhoto(
                    media=str(thumb_path),
                    caption=caption,
                )
            )

        logger.info("Uploading %d thumbnails as media group", len(media_group))
        await bot_client.send_media_group(
            chat_id=chat_id,
            media=media_group,
            reply_to_message_id=video_msg.id,
        )

    await video_queue.update_task_status(VideoStatus.UPLOADING, progress=100.0)
    logger.info("Upload complete for: %s", video_path.name)


def cleanup_files(video_path: Path, thumbnail_paths: list[Path]) -> None:
    """Remove all temporary local files after processing."""
    # Remove the video file
    if video_path.exists():
        video_path.unlink()
        logger.info("Deleted video: %s", video_path)

    # Remove thumbnail directory and files
    for tp in thumbnail_paths:
        if tp.exists():
            tp.unlink()

    # Remove thumbnail subdirectory if it exists
    thumb_dir = Config.THUMBNAIL_DIR / video_path.stem
    if thumb_dir.exists():
        shutil.rmtree(str(thumb_dir), ignore_errors=True)

    # Remove video thumbnail
    video_thumb = Config.THUMBNAIL_DIR / f"{video_path.stem}_video_thumb.jpg"
    if video_thumb.exists():
        video_thumb.unlink()

    logger.info("Cleanup complete for: %s", video_path.name)


async def process_single_video(bot_client, chat_id: int, task: VideoTask) -> bool:
    """
    Process a single video through the full pipeline.
    Returns True on success, False on failure.
    """
    video_path: Optional[Path] = None
    thumbnail_paths: list[Path] = []

    try:
        # Step 1: Download
        video_path = await download_video(task)

        # Step 2: Generate thumbnails
        thumbnail_paths = await generate_thumbnails(video_path)

        # Step 3: Upload to Telegram
        await upload_to_telegram(bot_client, chat_id, video_path, thumbnail_paths)

        # Step 4: Cleanup
        cleanup_files(video_path, thumbnail_paths)

        await video_queue.complete_current_task(success=True)
        return True

    except asyncio.CancelledError:
        logger.info("Processing cancelled for: %s", task.filename)
        if video_path:
            cleanup_files(video_path, thumbnail_paths)
        await video_queue.complete_current_task(success=False, error="Cancelled")
        return False

    except Exception as e:
        logger.error("Processing failed for %s: %s", task.filename, e, exc_info=True)
        if video_path:
            cleanup_files(video_path, thumbnail_paths)
        await video_queue.complete_current_task(success=False, error=str(e))

        # Notify user of failure
        try:
            await bot_client.send_message(
                chat_id=chat_id,
                text=f"❌ **Processing failed for:** `{task.filename}`\n\n**Error:** {str(e)[:500]}",
            )
        except Exception:
            pass

        return False


async def processing_loop(bot_client, chat_id: int) -> None:
    """
    Main processing loop. Pulls tasks from the queue one at a time
    and processes them sequentially.
    """
    logger.info("Processing loop started for chat_id: %d", chat_id)
    await video_queue.set_state(QueueState.PROCESSING)

    while not video_queue.is_cancelled():
        task = await video_queue.get_next_task()
        if task is None:
            # Queue is empty, check if we should keep waiting
            if video_queue._queue.empty() and not video_queue._pending_list:
                break
            continue

        logger.info(
            "Processing [%d/%d]: %s",
            video_queue.processed_count + 1,
            video_queue.total_videos,
            task.filename,
        )

        await process_single_video(bot_client, chat_id, task)

    if video_queue.state != QueueState.CANCELLED:
        await video_queue.set_state(QueueState.IDLE)

    logger.info(
        "Processing loop finished. %d/%d completed.",
        video_queue.processed_count,
        video_queue.total_videos,
    )
