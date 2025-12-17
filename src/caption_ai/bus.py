"""Segment bus for async queue management."""

import asyncio
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Segment:
    """A transcript segment with timestamp and text."""

    timestamp: datetime
    text: str
    speaker: str | None = None

    def __post_init__(self) -> None:
        """Ensure timestamp is datetime if string provided."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


class SegmentBus:
    """Async queue for managing transcript segments."""

    def __init__(self) -> None:
        """Initialize the segment bus."""
        self._queue: AsyncQueue[Segment] = asyncio.Queue()

    async def put(self, segment: Segment) -> None:
        """Add a segment to the queue."""
        await self._queue.put(segment)

    async def get(self) -> Segment:
        """Get a segment from the queue."""
        return await self._queue.get()

    def task_done(self) -> None:
        """Mark the current task as done."""
        self._queue.task_done()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def qsize(self) -> int:
        """Get queue size."""
        return self._queue.qsize()

