"""Screen streaming.

Browser dashboard (UI B): consumes MJPEG via <img src=".../stream">.
Native app  (UI A): can use the same MJPEG, or AVFoundation USB capture for
lowest latency (implemented on the Swift side — see native/).

Real mode proxies WDA's MJPEG broadcaster. Mock mode yields nothing; the
dashboard falls back to a client-side canvas labelled MOCK LIVE-VIEW.
"""
from __future__ import annotations

from typing import AsyncIterator

import httpx

from ..config import settings


def mjpeg_url(udid: str) -> str | None:
    dev = next((d for d in settings.devices if d.udid == udid), None)
    if not dev:
        return None
    return f"http://{dev.wda_host}:{dev.mjpeg_port}"


async def proxy_mjpeg(udid: str) -> AsyncIterator[bytes]:
    """Stream WDA MJPEG frames straight through to the client."""
    url = mjpeg_url(udid)
    if settings.mock_mode or not url:
        return
    async with httpx.AsyncClient(timeout=None) as c:
        async with c.stream("GET", url) as r:
            async for chunk in r.aiter_bytes():
                yield chunk
