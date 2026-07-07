"""
RAM Monitor — monitors system memory usage during video processing.

Prevents OOM crashes on lightweight VPS instances by pausing
processing when memory usage nears system limits.
"""

import logging
import shutil
from pathlib import Path

import psutil

from .config import Config

logger = logging.getLogger(__name__)


def get_ram_usage() -> dict:
    """Get current RAM usage statistics."""
    mem = psutil.virtual_memory()
    return {
        "total_mb": round(mem.total / (1024 * 1024), 1),
        "used_mb": round(mem.used / (1024 * 1024), 1),
        "available_mb": round(mem.available / (1024 * 1024), 1),
        "percent": mem.percent,
    }


def check_ram() -> bool:
    """
    Check if RAM usage is below the configured threshold.
    Returns True if safe to proceed, False if threshold exceeded.
    """
    usage = get_ram_usage()

    if usage["percent"] >= Config.RAM_CRITICAL_PERCENT:
        logger.critical(
            "CRITICAL RAM: %.1f%% used (%d MB / %d MB). Emergency action needed!",
            usage["percent"],
            usage["used_mb"],
            usage["total_mb"],
        )
        return False

    if usage["percent"] >= Config.RAM_THRESHOLD_PERCENT:
        logger.warning(
            "HIGH RAM: %.1f%% used (%d MB / %d MB). Pausing processing.",
            usage["percent"],
            usage["used_mb"],
            usage["total_mb"],
        )
        return False

    logger.debug(
        "RAM OK: %.1f%% used (%d MB available)",
        usage["percent"],
        usage["available_mb"],
    )
    return True


def emergency_cleanup(thumbnail_dir: Path) -> None:
    """
    Emergency cleanup when RAM is critically high.
    Removes temporary thumbnail files to free memory.
    """
    logger.warning("Emergency cleanup triggered — clearing temporary files")

    # Clear thumbnail directory
    if thumbnail_dir.exists():
        for item in thumbnail_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(str(item), ignore_errors=True)
                else:
                    item.unlink()
            except Exception as e:
                logger.error("Failed to remove %s: %s", item, e)

    # Force garbage collection
    import gc
    gc.collect()

    usage = get_ram_usage()
    logger.info(
        "After emergency cleanup: %.1f%% RAM used (%d MB available)",
        usage["percent"],
        usage["available_mb"],
    )


def log_ram_status() -> dict:
    """Log and return current RAM status for monitoring."""
    usage = get_ram_usage()
    status = "OK"
    if usage["percent"] >= Config.RAM_CRITICAL_PERCENT:
        status = "CRITICAL"
    elif usage["percent"] >= Config.RAM_THRESHOLD_PERCENT:
        status = "HIGH"

    logger.info(
        "RAM [%s]: %.1f%% — %d MB used / %d MB total (%d MB free)",
        status,
        usage["percent"],
        usage["used_mb"],
        usage["total_mb"],
        usage["available_mb"],
    )
    return {**usage, "status": status}
