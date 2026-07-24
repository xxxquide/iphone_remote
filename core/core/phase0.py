"""Phase 0 Doctor — one command to validate the real-device setup.

    python -m core.phase0        # or: make doctor

Runs structured checks (tools, devices, WDA, tunnel, TikTok app, config) and
prints a report with pass/warn/fail and a concrete fix for anything wrong. It
knows about the two known landmines: the Xcode 26 WDA provisioning bug and the
go-ios userspace-tunnel regression on iOS 26.4-26.5 (#772).

Exit code is non-zero if any check FAILs, so it can gate a setup script.
In mock mode (default) device checks are marked SKIP so the report still renders.
"""
from __future__ import annotations

import asyncio
import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import httpx

from .bridge import devicectl
from .config import settings


class Status(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class Check:
    name: str
    status: Status
    detail: str = ""
    fix: str = ""


REQUIRED_TOOLS = [
    ("xcrun", "Xcode CLT / devicectl", "xcode-select --install (and install Xcode 26)"),
    ("appium", "Appium server", "npm i -g appium && appium driver install xcuitest"),
    ("pymobiledevice3", "iOS 17+ tunnel + screen stream", "pip install -U pymobiledevice3"),
    ("ffmpeg", "media / stream tooling", "brew install ffmpeg"),
]
OPTIONAL_TOOLS = [
    ("ios", "go-ios (alternative tunnel)", "brew install go-ios"),
    ("visionocr", "Apple Vision OCR helper",
     "cd tools/visionocr && swift build -c release && cp .build/release/visionocr /usr/local/bin/"),
]


def check_tool(cmd: str, desc: str, fix: str, required: bool = True) -> Check:
    if shutil.which(cmd):
        return Check(f"tool: {cmd}", Status.PASS, desc)
    return Check(f"tool: {cmd}", Status.FAIL if required else Status.WARN,
                 f"{desc} — not found on PATH", fix)


def ios_tooling_warning(ios: str) -> Optional[Check]:
    """go-ios userspace tunnel regressed on iOS 26.4-26.5 (#772)."""
    if any(ios.startswith(b) for b in ("26.4", "26.5")):
        return Check(f"iOS {ios} tooling", Status.WARN,
                     "go-ios userspace tunnel regressed on 26.4-26.5 (#772)",
                     "use pymobiledevice3 tunneld, or keep 15 Pro Max on 26.2-26.3")
    return None


async def check_wda(dev) -> Check:
    url = f"http://{dev.wda_host}:{dev.wda_port}/status"
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(url)
        ok = r.status_code == 200
        return Check(f"WDA: {dev.name}", Status.PASS if ok else Status.FAIL,
                     f"{url} -> {r.status_code}",
                     "" if ok else "sign+launch WDA and open the tunnel (docs/SIGNING.md)")
    except Exception as e:  # noqa: BLE001
        return Check(f"WDA: {dev.name}", Status.FAIL, f"unreachable ({e})",
                     "sign+launch WDA (usePreinstalledWDA), open iOS17+ tunnel, forward wda_port")


async def run_all() -> list[Check]:
    checks: list[Check] = []

    # --- config sanity ---
    checks.append(
        Check("config: media token", Status.PASS)
        if settings.media_token != "change-me-media-token"
        else Check("config: media token", Status.WARN, "still the default",
                   "set ORCH_MEDIA_TOKEN in .env before real media handoff"))
    checks.append(Check("config: LAN host", Status.PASS, settings.lan_host or "unknown"))
    if settings.llm_enabled and not settings.llm_api_key:
        checks.append(Check("config: LLM", Status.WARN, "enabled but no API key",
                            "set ORCH_LLM_API_KEY or disable ORCH_LLM_ENABLED"))

    # --- tools ---
    for cmd, desc, fix in REQUIRED_TOOLS:
        checks.append(check_tool(cmd, desc, fix, required=True))
    for cmd, desc, fix in OPTIONAL_TOOLS:
        checks.append(check_tool(cmd, desc, fix, required=False))

    # --- devices ---
    listed = await devicectl.list_devices()
    listed_udids = {d["udid"] for d in listed}
    if not listed and not settings.mock_mode:
        checks.append(Check("devices: visible", Status.FAIL, "none via devicectl",
                            "connect USB, tap Trust This Computer, enable Developer Mode"))

    for dev in settings.devices:
        present = settings.mock_mode or dev.udid in listed_udids
        checks.append(Check(f"device: {dev.name}",
                            Status.PASS if present else Status.FAIL,
                            dev.udid if present else "not found via devicectl",
                            "" if present else "fix devices.json UDID / USB / Trust"))
        warn = ios_tooling_warning(dev.ios)
        if warn:
            checks.append(warn)
        if settings.mock_mode:
            checks.append(Check(f"WDA: {dev.name}", Status.SKIP, "mock mode"))
            continue
        checks.append(await check_wda(dev))
        apps = await devicectl.list_apps(dev.udid)
        has_tt = any("zhiliao" in a.lower() or "musically" in a.lower() for a in apps)
        checks.append(Check(f"TikTok app: {dev.name}",
                            Status.PASS if has_tt else Status.WARN,
                            dev.tiktok_bundle_id if has_tt else "not detected",
                            "" if has_tt else "install TikTok and confirm its bundle id"))

    # --- things we cannot verify remotely ---
    checks.append(Check("shortcut: OrchSaveToPhotos", Status.SKIP,
                        "cannot verify remotely",
                        "create the Shortcut on each phone (docs/ARCHITECTURE.md)"))
    return checks


def summarize(checks: list[Check]) -> tuple[dict, int]:
    counts = {s: 0 for s in Status}
    for c in checks:
        counts[c.status] += 1
    return counts, (1 if counts[Status.FAIL] else 0)


def render(checks: list[Check]) -> str:
    icon = {Status.PASS: "✓", Status.WARN: "!", Status.FAIL: "✗", Status.SKIP: "·"}
    out = ["", "  Phase 0 Doctor — iphone-orchestrator",
           f"  mode: {'MOCK' if settings.mock_mode else 'REAL DEVICES'}",
           "  " + "-" * 50]
    for c in checks:
        line = f"  {icon[c.status]} [{c.status.value:<4}] {c.name}"
        if c.detail:
            line += f" — {c.detail}"
        out.append(line)
        if c.fix and c.status in (Status.FAIL, Status.WARN):
            out.append(f"         ↳ fix: {c.fix}")
    counts, _ = summarize(checks)
    out += ["  " + "-" * 50,
            f"  PASS {counts[Status.PASS]}   WARN {counts[Status.WARN]}   "
            f"FAIL {counts[Status.FAIL]}   SKIP {counts[Status.SKIP]}", ""]
    return "\n".join(out)


def main() -> None:
    checks = asyncio.run(run_all())
    print(render(checks))
    _, code = summarize(checks)
    sys.exit(code)


if __name__ == "__main__":
    main()
