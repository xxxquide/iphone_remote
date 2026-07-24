"""put_media — get a video into the iPhone Photos library from the Mac.

There is no supported way to write straight into Photos from `devicectl`. The
reliable, no-jailbreak pattern is a small user-created **Shortcut** that fetches
a file from the Mac over the LAN and saves it to Photos:

  Shortcut "OrchSaveToPhotos" (one-time, on each phone):
    1. Receive input (Text)                 -> the media URL
    2. Get contents of URL (that text)      -> downloads the video
    3. Save to Photos Album
  Enable it to run without confirmation where possible.

We trigger it with a URL scheme via devicectl openURL:
  shortcuts://x-callback-url/run-shortcut?name=OrchSaveToPhotos&input=text&text=<media_url>

The media_url points at the core's LAN media route (see api.py /media/...).

CAVEATS (verify in Phase 0):
  * The core must be reachable from the phone (bind API to LAN, or run a small
    LAN media server). With a full-tunnel VPN on the phone, LAN routes may be
    captured — test, or use a split-tunnel/allow-LAN setting.
  * Shortcuts confirmation prompts vary by iOS version (fragile on iOS 18.2+).
Alternative paths if this proves unreliable: iCloud/Files sync, or a tiny
on-device helper app with a "save media" App Intent (costs a signing slot).
"""
from __future__ import annotations

import shutil
import urllib.parse
from pathlib import Path
from typing import Optional

from .bridge import devicectl
from .config import settings


def media_url(filename: str) -> str:
    return (f"http://{settings.lan_host}:{settings.port}"
            f"/media/{settings.media_token}/{urllib.parse.quote(filename)}")


def stage_media(src_path: str) -> Optional[str]:
    """Copy the source file into the served media dir; return its filename."""
    src = Path(src_path)
    if not src.exists():
        return None
    dest = Path(settings.media_dir) / src.name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return src.name


async def put_media(udid: str, src_path: str) -> bool:
    """Stage the file, then ask the phone's Shortcut to fetch + save to Photos."""
    if settings.mock_mode:
        return True
    filename = stage_media(src_path)
    if not filename:
        return False
    url = media_url(filename)
    deep_link = (
        "shortcuts://x-callback-url/run-shortcut?"
        + urllib.parse.urlencode({
            "name": settings.shortcut_save_photos,
            "input": "text",
            "text": url,
        })
    )
    return await devicectl.open_url(udid, deep_link)
