"""Tiny async pub/sub event bus, broadcast to all WebSocket subscribers."""
from __future__ import annotations

import asyncio
import time
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def emit(self, type_: str, **data: Any) -> None:
        evt = {"type": type_, "ts": time.time(), **data}
        for q in list(self._subscribers):
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                # Drop for slow consumers; live-view/log events are best-effort.
                pass

    def emit_soon(self, type_: str, **data: Any) -> None:
        """Fire-and-forget from sync contexts."""
        try:
            asyncio.get_running_loop().create_task(self.emit(type_, **data))
        except RuntimeError:
            pass


bus = EventBus()
