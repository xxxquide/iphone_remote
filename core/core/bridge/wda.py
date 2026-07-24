"""WebDriverAgent HTTP client — tap / type / element tree / status.

WDA speaks a JSONWire-ish HTTP protocol on a device-local port (default 8100),
forwarded to the Mac via the iOS 17+ tunnel (see tunnel.py). MJPEG frames are
broadcast on a separate port (default 9100) — proxied in streaming.py.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from ..config import DeviceConfig, settings


class WDAClient:
    def __init__(self, dev: DeviceConfig) -> None:
        self.dev = dev
        self.base = f"http://{dev.wda_host}:{dev.wda_port}"
        self._session: Optional[str] = None

    async def status(self) -> dict[str, Any]:
        if settings.mock_mode:
            return {"ready": True, "mock": True}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{self.base}/status")
            return r.json()

    async def ensure_session(self, bundle_id: str = "") -> str:
        if settings.mock_mode:
            self._session = "mock-session"
            return self._session
        caps: dict[str, Any] = {"capabilities": {"alwaysMatch": {}}}
        if bundle_id:
            caps["capabilities"]["alwaysMatch"]["bundleId"] = bundle_id
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{self.base}/session", json=caps)
            self._session = r.json()["value"]["sessionId"]
        return self._session

    async def tap(self, x: float, y: float) -> None:
        if settings.mock_mode:
            return
        sid = await self.ensure_session()
        payload = {"actions": [{
            "type": "pointer", "id": "finger1", "parameters": {"pointerType": "touch"},
            "actions": [
                {"type": "pointerMove", "duration": 0, "x": int(x), "y": int(y)},
                {"type": "pointerDown", "button": 0},
                {"type": "pause", "duration": 60},
                {"type": "pointerUp", "button": 0},
            ],
        }]}
        async with httpx.AsyncClient(timeout=15) as c:
            await c.post(f"{self.base}/session/{sid}/actions", json=payload)

    async def type_text(self, text: str) -> None:
        if settings.mock_mode:
            return
        sid = await self.ensure_session()
        async with httpx.AsyncClient(timeout=15) as c:
            await c.post(f"{self.base}/session/{sid}/wda/keys", json={"value": list(text)})

    async def source(self) -> dict[str, Any]:
        """Accessibility tree (used by the vision/targeting cascade, level 1)."""
        if settings.mock_mode:
            return {"value": {"type": "Application", "children": []}, "mock": True}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{self.base}/source?format=json")
            return r.json()

    async def activate_app(self, bundle_id: str) -> None:
        if settings.mock_mode:
            return
        sid = await self.ensure_session()
        async with httpx.AsyncClient(timeout=20) as c:
            await c.post(f"{self.base}/session/{sid}/wda/apps/activate",
                         json={"bundleId": bundle_id})


def client_for(udid: str) -> WDAClient:
    dev = next((d for d in settings.devices if d.udid == udid), None)
    if not dev:
        raise KeyError(f"unknown device {udid}")
    return WDAClient(dev)
