"""
Queue Manager — enforces strict sequential video processing.

Uses asyncio.Queue to ensure only one video is processed at a time.
Emits state changes to all connected WebSocket clients.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class VideoStatus(str, Enum):
    """Status of an individual video in the queue."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    GENERATING_THUMBNAILS = "generating_thumbnails"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueueState(str, Enum):
    """Overall state of the processing queue."""
    IDLE = "idle"
    PROCESSING = "processing"
    PAUSED_RAM = "paused_ram"
    CANCELLED = "cancelled"


@dataclass
class VideoTask:
    """Represents a single video to be processed."""
    filename: str
    remote_path: str
    file_size: int = 0  # bytes
    file_size_human: str = ""
    status: VideoStatus = VideoStatus.PENDING
    progress: float = 0.0  # 0-100
    error: str = ""
    speed: str = ""  # e.g. "12.5 MB/s"
    added_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for WebSocket transmission."""
        return {
            "filename": self.filename,
            "remote_path": self.remote_path,
            "file_size": self.file_size,
            "file_size_human": self.file_size_human,
            "status": self.status.value,
            "progress": self.progress,
            "error": self.error,
            "speed": self.speed,
            "added_at": self.added_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class VideoQueue:
    """
    Manages the video processing queue with strict sequential execution.

    Only one video is processed at a time. State changes are broadcast
    to connected WebSocket clients via the on_state_change callback.
    """

    def __init__(self):
        self._queue: asyncio.Queue[VideoTask] = asyncio.Queue()
        self._pending_list: list[VideoTask] = []
        self._completed_list: list[VideoTask] = []
        self._current_task: Optional[VideoTask] = None
        self._state: QueueState = QueueState.IDLE
        self._total_videos: int = 0
        self._processed_count: int = 0
        self._is_running: bool = False
        self._cancel_event: asyncio.Event = asyncio.Event()

        # Callback for broadcasting state changes
        self._on_state_change: Optional[Callable[[], Awaitable[None]]] = None

    @property
    def state(self) -> QueueState:
        return self._state

    @property
    def current_task(self) -> Optional[VideoTask]:
        return self._current_task

    @property
    def pending_list(self) -> list[VideoTask]:
        return self._pending_list.copy()

    @property
    def completed_list(self) -> list[VideoTask]:
        return self._completed_list.copy()

    @property
    def total_videos(self) -> int:
        return self._total_videos

    @property
    def processed_count(self) -> int:
        return self._processed_count

    @property
    def is_running(self) -> bool:
        return self._is_running

    def set_state_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Set the callback to invoke when queue state changes."""
        self._on_state_change = callback

    async def _notify_state_change(self) -> None:
        """Notify all listeners of a state change."""
        if self._on_state_change:
            try:
                await self._on_state_change()
            except Exception as e:
                logger.error("Error in state change callback: %s", e)

    async def add_task(self, task: VideoTask) -> None:
        """Add a video task to the queue."""
        self._pending_list.append(task)
        await self._queue.put(task)
        self._total_videos += 1
        logger.info("Added to queue: %s (%s)", task.filename, task.file_size_human)
        await self._notify_state_change()

    async def add_tasks(self, tasks: list[VideoTask]) -> None:
        """Add multiple video tasks to the queue at once."""
        for task in tasks:
            self._pending_list.append(task)
            await self._queue.put(task)
            self._total_videos += 1
        logger.info("Added %d videos to queue", len(tasks))
        await self._notify_state_change()

    async def get_next_task(self) -> Optional[VideoTask]:
        """Get the next task from the queue. Blocks until available."""
        try:
            task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            # Remove from pending list
            if task in self._pending_list:
                self._pending_list.remove(task)
            self._current_task = task
            task.started_at = time.time()
            return task
        except asyncio.TimeoutError:
            return None

    async def update_task_status(
        self, status: VideoStatus, progress: float = 0.0, error: str = "", speed: Optional[str] = None
    ) -> None:
        """Update the status of the currently processing task."""
        if self._current_task:
            if self._current_task.status != status:
                self._current_task.speed = speed if speed is not None else ""
            elif speed is not None:
                self._current_task.speed = speed
            self._current_task.status = status
            self._current_task.progress = progress
            self._current_task.error = error
            await self._notify_state_change()

    async def complete_current_task(self, success: bool = True, error: str = "") -> None:
        """Mark the current task as completed or failed."""
        if self._current_task:
            self._current_task.completed_at = time.time()
            if success:
                self._current_task.status = VideoStatus.COMPLETED
                self._current_task.progress = 100.0
            else:
                self._current_task.status = VideoStatus.FAILED
                self._current_task.error = error

            self._completed_list.append(self._current_task)
            self._processed_count += 1
            self._current_task = None
            self._queue.task_done()
            await self._notify_state_change()

    async def set_state(self, state: QueueState) -> None:
        """Update the overall queue state."""
        self._state = state
        logger.info("Queue state changed to: %s", state.value)
        await self._notify_state_change()

    def request_cancel(self) -> None:
        """Signal cancellation of the current processing."""
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel_event.is_set()

    async def cancel_all(self) -> None:
        """Cancel all pending tasks and stop processing."""
        self._cancel_event.set()

        # Drain the queue
        while not self._queue.empty():
            try:
                task = self._queue.get_nowait()
                task.status = VideoStatus.CANCELLED
                self._completed_list.append(task)
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

        self._pending_list.clear()

        if self._current_task:
            self._current_task.status = VideoStatus.CANCELLED
            self._completed_list.append(self._current_task)
            self._current_task = None

        await self.set_state(QueueState.CANCELLED)
        logger.info("All tasks cancelled")

    def reset(self) -> None:
        """Reset the queue for a new batch of processing."""
        self._queue = asyncio.Queue()
        self._pending_list.clear()
        self._completed_list.clear()
        self._current_task = None
        self._state = QueueState.IDLE
        self._total_videos = 0
        self._processed_count = 0
        self._cancel_event.clear()

    def get_full_status(self) -> dict:
        """Get the complete queue status for WebSocket broadcast."""
        return {
            "state": self._state.value,
            "current_task": self._current_task.to_dict() if self._current_task else None,
            "pending": [t.to_dict() for t in self._pending_list],
            "completed": [t.to_dict() for t in self._completed_list[-20:]],  # Last 20
            "total_videos": self._total_videos,
            "processed_count": self._processed_count,
            "progress_percent": (
                round((self._processed_count / self._total_videos) * 100, 1)
                if self._total_videos > 0
                else 0
            ),
        }


# Singleton instance
video_queue = VideoQueue()
