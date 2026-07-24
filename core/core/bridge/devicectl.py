"""Apple `devicectl` (CoreDevice) wrapper — the OS-sanctioned control lever.

Covers: list devices, screenshot, open URL (deep-link), launch app, info.
Requires: Xcode 15+, a paired+trusted device, Developer Mode, mounted DDI.
None of these need a *paid* developer account (WDA signing does — see signing/).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ..config import settings
from .base import run_cmd


async def list_devices() -> list[dict]:
    if settings.mock_mode:
        return [{"udid": d.udid, "name": d.name, "ios": d.ios} for d in settings.devices]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    res = await run_cmd(["xcrun", "devicectl", "list", "devices", "--json-output", out_path])
    if not res.ok:
        return []
    data = json.loads(Path(out_path).read_text())
    devs = []
    for d in data.get("result", {}).get("devices", []):
        props = d.get("deviceProperties", {})
        hw = d.get("hardwareProperties", {})
        devs.append({
            "udid": hw.get("udid", ""),
            "name": props.get("name", ""),
            "ios": props.get("osVersionNumber", ""),
        })
    return devs


async def screenshot(udid: str, dest: str) -> bool:
    if settings.mock_mode:
        return False  # mock stream is drawn client-side; see web/app.js
    res = await run_cmd(["xcrun", "devicectl", "device", "screenshot",
                         "--device", udid, dest], timeout=30)
    return res.ok


async def capture_screenshot(udid: str) -> str | None:
    """Take a screenshot to a temp PNG and return its path (None in mock)."""
    if settings.mock_mode:
        return None
    import tempfile
    fd = tempfile.NamedTemporaryFile(prefix=f"orch_{udid}_", suffix=".png", delete=False)
    fd.close()
    return fd.name if await screenshot(udid, fd.name) else None


async def open_url(udid: str, url: str) -> bool:
    if settings.mock_mode:
        return True
    res = await run_cmd(["xcrun", "devicectl", "device", "process", "openURL",
                         "--device", udid, url], timeout=30)
    return res.ok


async def launch_app(udid: str, bundle_id: str) -> bool:
    if settings.mock_mode:
        return True
    res = await run_cmd(["xcrun", "devicectl", "device", "process", "launch",
                         "--device", udid, bundle_id], timeout=30)
    return res.ok


async def list_apps(udid: str) -> list[str]:
    """Handy for Phase 0: confirm TikTok's bundle id on the device."""
    if settings.mock_mode:
        return ["com.zhiliaoapp.musically", "com.apple.Preferences"]
    res = await run_cmd(["xcrun", "devicectl", "device", "info", "apps",
                         "--device", udid])
    return [ln for ln in res.out.splitlines() if "." in ln]
