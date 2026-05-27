"""In-process pub/sub for signals. WebSocket clients subscribe; publish-node pushes."""
from __future__ import annotations

import asyncio
from typing import Any

from src.utils.logging import get_logger

log = get_logger(__name__)


class SignalBroadcaster:
    """Fan-out queue. Each subscriber gets a private asyncio.Queue.

    Slow consumers don't slow producers — if a queue is full, the message is dropped
    for that client only (with a warning), and live publishing continues.
    """

    def __init__(self, queue_size: int = 100):
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._queue_size = queue_size
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            self._subscribers.add(q)
        log.info("websocket subscriber added (total=%d)", len(self._subscribers))
        return q

    async def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._subscribers.discard(q)
        log.info("websocket subscriber removed (total=%d)", len(self._subscribers))

    async def publish(self, message: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._subscribers)
        dropped = 0
        for q in targets:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                dropped += 1
        if dropped:
            log.warning("dropped message for %d slow subscriber(s)", dropped)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
