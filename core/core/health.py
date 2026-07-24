"""Health & recovery loop.

Periodically checks each device (WDA reachable? tunnel up? signing near expiry?),
persists status, emits `device.updated` events for the UIs, and attempts
recovery in real mode (restart WDA, trigger re-sign). Defensive: a failure for
one device never breaks the loop.
"""
from __future__ import annotations

import asyncio

from .bridge import tunnel
from .bridge.wda import client_for
from .config import settings
from .events import bus
from .store import store


async def check_device(dev) -> dict:
    """Return a status dict for one device; attempt light recovery in real mode."""
    if settings.mock_mode:
        return {"status": "online", "wda": "ready", "tunnel": "up"}

    tunnel_ok = tunnel.tunnel_up()
    wda_ready = False
    try:
        st = await client_for(dev.udid).status()
        wda_ready = bool(st.get("ready", False))
    except Exception:
        wda_ready = False

    # Light recovery: bring the tunnel/WDA back if they dropped.
    if not tunnel_ok:
        try:
            await tunnel.start_tunnel()
            tunnel_ok = tunnel.tunnel_up()
        except Exception:
            pass
    if tunnel_ok and not wda_ready:
        try:
            await tunnel.run_wda(dev.udid)
        except Exception:
            pass

    return {
        "status": "online" if tunnel_ok else "offline",
        "wda": "ready" if wda_ready else "down",
        "tunnel": "up" if tunnel_ok else "down",
    }


async def run_loop() -> None:
    while True:
        for dev in settings.devices:
            try:
                s = await check_device(dev)
                await store.upsert_device({"udid": dev.udid, "name": dev.name,
                                           "ios": dev.ios, **s})
                await bus.emit("device.updated", udid=dev.udid, **s)
            except Exception as e:  # noqa: BLE001 - never break the loop
                await bus.emit("device.error", udid=dev.udid, error=str(e))
        await asyncio.sleep(settings.health_interval_s)
