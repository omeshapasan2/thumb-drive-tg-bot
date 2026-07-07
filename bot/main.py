"""
Main entry point — starts both the Pyrogram bot and FastAPI WebSocket server.

Runs both services concurrently using asyncio.
"""

import asyncio
import logging
import signal
import sys
import uvicorn

from bot.config import Config
from bot.client import create_bot_client
from bot.ws_server import app as fastapi_app

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(name)-25s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Quiet noisy loggers
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("bot.main")


async def run_bot(bot_client):
    """Start and run the Pyrogram bot."""
    logger.info("Starting Pyrogram bot...")
    await bot_client.start()
    logger.info("Bot is running! Waiting for messages...")

    # Keep the bot running
    await asyncio.Event().wait()


async def run_websocket_server():
    """Start the FastAPI WebSocket server."""
    config = uvicorn.Config(
        app=fastapi_app,
        host="0.0.0.0",
        port=Config.WS_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    logger.info("Starting WebSocket server on port %d...", Config.WS_PORT)
    await server.serve()


async def main():
    """Main entry point — runs bot and WebSocket server concurrently."""
    # Validate configuration
    Config.validate()

    logger.info("=" * 60)
    logger.info("  Video Thumbnail Generator Bot")
    logger.info("=" * 60)
    logger.info("  API ID:      %s", Config.API_ID)
    logger.info("  Protocol:    MTProto (native 2GB upload support)")
    logger.info("  Remote:      %s", Config.RCLONE_REMOTE)
    logger.info("  Drive Path:  %s", Config.RCLONE_PATH)
    logger.info("  Download:    %s", Config.DOWNLOAD_DIR)
    logger.info("  Thumbnails:  %s", Config.THUMBNAIL_DIR)
    logger.info("  WS Port:     %d", Config.WS_PORT)
    logger.info("  RAM Limit:   %d%%", Config.RAM_THRESHOLD_PERCENT)
    logger.info("=" * 60)

    # Create the bot client
    bot_client = create_bot_client()

    # Run both services concurrently
    try:
        await asyncio.gather(
            run_bot(bot_client),
            run_websocket_server(),
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        if bot_client.is_connected:
            await bot_client.stop()
        logger.info("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
