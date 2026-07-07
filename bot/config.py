"""
Configuration module — all settings from environment variables.
Uses pathlib for robust file path handling.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration loaded from environment variables."""

    # --- Telegram API credentials ---
    API_ID: int = int(os.getenv("API_ID", "0"))
    API_HASH: str = os.getenv("API_HASH", "")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # --- rclone settings ---
    RCLONE_REMOTE: str = os.getenv("RCLONE_REMOTE", "gdrive")
    RCLONE_PATH: str = os.getenv("RCLONE_PATH", "/")

    # --- File paths (absolute, via pathlib) ---
    BASE_DIR: Path = Path(os.getenv("BASE_DIR", "/app")).resolve()
    DOWNLOAD_DIR: Path = Path(os.getenv("DOWNLOAD_DIR", "/app/downloads")).resolve()
    THUMBNAIL_DIR: Path = Path(os.getenv("THUMBNAIL_DIR", "/app/thumbnails")).resolve()

    # --- Web App ---
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://your-domain.com")
    WS_PORT: int = int(os.getenv("WS_PORT", "8765"))

    # --- Target Channel for uploads (optional: channel username or ID e.g. @mychannel or -1001234567890) ---
    TARGET_CHANNEL: str = os.getenv("TARGET_CHANNEL", "").strip().strip('"').strip("'")

    # --- RAM monitoring ---
    RAM_THRESHOLD_PERCENT: int = int(os.getenv("RAM_THRESHOLD_PERCENT", "85"))
    RAM_CRITICAL_PERCENT: int = int(os.getenv("RAM_CRITICAL_PERCENT", "95"))

    # --- Authorized users (space-separated user IDs, 0 = public) ---
    AUTH_USERS: list[int] = [
        int(uid) for uid in os.getenv("AUTH_USERS", "0").split() if uid.strip()
    ]

    # --- Video extensions to process ---
    VIDEO_EXTENSIONS: set[str] = {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
        ".webm", ".m4v", ".ts", ".mpeg", ".mpg", ".3gp",
    }

    @classmethod
    def validate(cls) -> None:
        """Validate that all required configuration is present."""
        errors = []

        if not cls.API_ID:
            errors.append("API_ID is required")
        if not cls.API_HASH:
            errors.append("API_HASH is required")
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is required")

        if errors:
            for err in errors:
                print(f"[CONFIG ERROR] {err}", file=sys.stderr)
            sys.exit(1)

        # Ensure download and thumbnail directories exist
        cls.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def is_authorized(cls, user_id: int) -> bool:
        """Check if a user is authorized to use the bot."""
        if 0 in cls.AUTH_USERS:
            return True
        return user_id in cls.AUTH_USERS
