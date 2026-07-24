"""VPN / IP management — VPN lives ON EACH iPhone (own IP per phone).

The core does not route phone traffic; it VERIFIES the phone's egress IP before a
run and enforces a 'rotate every N runs' policy.

Measuring the phone's egress IP without an on-device app: open a plaintext
ip-echo (api.ipify.org) via devicectl openURL, screenshot, OCR the IP, then do a
Mac-side geo lookup for the region. Reliability varies (Safari chrome, OCR) —
verify in Phase 0; an on-device Shortcut that reports back is the sturdier v2.

HONEST CAVEAT: datacenter IPs from commercial VPNs (ExpressVPN etc.) are often
flagged by TikTok/IG. This module manages + verifies; it does not defeat detection.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from .bridge import devicectl
from .config import settings
from .vision import ocr as ocr_mod

_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")


@dataclass
class VpnState:
    udid: str
    connected: bool = False
    ip: Optional[str] = None
    region: Optional[str] = None
    runs_since_rotation: int = 0


_states: dict[str, VpnState] = {}


def state_for(udid: str) -> VpnState:
    return _states.setdefault(udid, VpnState(udid=udid))


def extract_ip(text: str) -> Optional[str]:
    m = _IPV4.search(text or "")
    return m.group(0) if m else None


async def _geo_region(ip: str) -> Optional[str]:
    """Best-effort country lookup for the detected IP (Mac-side)."""
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r = await c.get(f"http://ip-api.com/json/{ip}?fields=countryCode")
            return r.json().get("countryCode")
    except Exception:
        return None


async def verify_ip(udid: str, expected_region: str = "") -> VpnState:
    st = state_for(udid)
    if settings.mock_mode:
        st.connected = True
        st.ip = "203.0.113.42"                 # TEST-NET placeholder
        st.region = expected_region or "US"
        return st

    await devicectl.open_url(udid, "https://api.ipify.org")
    await asyncio.sleep(3.0)                    # let Safari load
    shot = await devicectl.capture_screenshot(udid)
    ip = None
    if shot:
        ocr = ocr_mod.get_ocr()
        if ocr.available():
            text = " ".join(w.text for w in ocr.recognize(shot))
            ip = extract_ip(text)
    st.ip = ip
    st.connected = ip is not None
    st.region = await _geo_region(ip) if ip else None
    return st


def note_run(udid: str, rotate_every: int = 5) -> bool:
    """Increment run counter; return True when an IP rotation is due."""
    st = state_for(udid)
    st.runs_since_rotation += 1
    if st.runs_since_rotation >= rotate_every:
        st.runs_since_rotation = 0
        return True
    return False
