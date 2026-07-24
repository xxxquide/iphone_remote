"""Signing Manager — keep WebDriverAgent alive on a FREE Apple ID.

Free-account facts (confirmed 2026):
  * profile valid 7 days  * ~3 App ID slots (WDA uses 2)  * manual Trust once
  * device needs internet to validate signing (iOS 16+)

Strategy (AltStore model — the Mac is always nearby):
  1) one-time: sign WDA via Xcode GUI, Trust on each device, export .p12
  2) detect expiry proactively (profile date or WDA launch failure)
  3) re-sign with resigner / `appium sign-wda`, reinstall, verify

This module orchestrates; the actual codesign work lives in
scripts/resign_wda.sh so it is easy to run/cron independently.
"""
from __future__ import annotations

import plistlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import REPO_ROOT, settings


def days_left(profile_path: str) -> Optional[int]:
    """Read a .mobileprovision expiration date; days until it lapses."""
    p = Path(profile_path)
    if not p.exists():
        return None
    try:
        # profiles are CMS-wrapped; extract the plist
        raw = subprocess.run(["security", "cms", "-D", "-i", str(p)],
                             capture_output=True).stdout
        data = plistlib.loads(raw)
        exp = data.get("ExpirationDate")
        if isinstance(exp, datetime):
            delta = exp.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
            return delta.days
    except Exception:
        return None
    return None


def needs_resign(profile_path: str) -> bool:
    d = days_left(profile_path)
    return d is None or d <= settings.wda_resign_days


def resign(udid: str) -> bool:
    """Invoke the bash helper to re-sign + reinstall WDA for a device."""
    if settings.mock_mode:
        return True
    script = REPO_ROOT / "core" / "scripts" / "resign_wda.sh"
    res = subprocess.run(["bash", str(script), udid], text=True)
    return res.returncode == 0
