"""
Custom Pyrogram client for the Video Thumbnail Generator Bot.

Pyrogram uses the MTProto protocol, which connects directly to Telegram
servers and already bypasses the 50MB file size limit imposed by the
official Bot HTTP API. No local Bot API server is needed.

The 2GB upload limit applies to bot accounts via MTProto.
"""

import logging
from pyrogram import Client

from .config import Config

logger = logging.getLogger(__name__)


def create_bot_client() -> Client:
    """
    Create and return a Pyrogram Client.

    Pyrogram communicates via MTProto (not the HTTP Bot API), so it
    natively supports uploading files up to 2GB without needing a
    local Bot API server.
    """
    logger.info("Initializing Pyrogram MTProto client")

    bot = Client(
        name="video_thumb_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        plugins=dict(root="bot/plugins"),
        workdir=str(Config.BASE_DIR),
    )

    return bot
