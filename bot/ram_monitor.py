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


import time

_last_net_io = [None]
_last_net_time = [0.0]


def get_network_speed() -> dict:
    """Get container network download and upload speeds (in bytes/sec and formatted strings)."""
    now = time.time()
    try:
        net_io = psutil.net_io_counters()
    except Exception:
        return {"download_speed": "0 B/s", "upload_speed": "0 B/s", "recv_bps": 0, "sent_bps": 0}

    if _last_net_io[0] is None or _last_net_time[0] == 0.0:
        _last_net_io[0] = net_io
        _last_net_time[0] = now
        return {"download_speed": "0 B/s", "upload_speed": "0 B/s", "recv_bps": 0, "sent_bps": 0}

    time_diff = now - _last_net_time[0]
    if time_diff < 0.5:
        time_diff = 0.5

    recv_diff = max(0, net_io.bytes_recv - _last_net_io[0].bytes_recv)
    sent_diff = max(0, net_io.bytes_sent - _last_net_io[0].bytes_sent)

    _last_net_io[0] = net_io
    _last_net_time[0] = now

    recv_bps = recv_diff / time_diff
    sent_bps = sent_diff / time_diff

    def format_speed(bps: float) -> str:
        if bps >= 1024 * 1024:
            return f"{bps / (1024 * 1024):.2f} MB/s"
        elif bps >= 1024:
            return f"{bps / 1024:.1f} KB/s"
        else:
            return f"{bps:.0f} B/s"

    return {
        "download_speed": format_speed(recv_bps),
        "upload_speed": format_speed(sent_bps),
        "recv_bps": round(recv_bps),
        "sent_bps": round(sent_bps),
    }


def log_ram_status() -> dict:
    """Log and return current RAM status and container network speed for monitoring."""
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
    return {**usage, "status": status, "net": get_network_speed()}
