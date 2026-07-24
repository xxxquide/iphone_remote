"""Configuration for the core service.

Loads settings from environment variables and an optional .env file.
Kept dependency-free (no pydantic-settings) so the skeleton starts fast.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines). No external dependency."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv(REPO_ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class DeviceConfig:
    """One managed iPhone. Populated from devices.json or mock defaults."""
    udid: str
    name: str
    ios: str
    wda_host: str = "127.0.0.1"
    wda_port: int = 8100          # per-device local port that WDA is forwarded to
    mjpeg_port: int = 9100        # WDA MJPEG broadcaster port (forwarded)
    tiktok_bundle_id: str = "com.zhiliaoapp.musically"  # VERIFY on device (Phase 0)
    vpn_expected_region: str = ""  # e.g. "US"; empty = skip IP verification
    scale: float = 3.0             # screenshot px -> logical points (both phones = @3x)


@dataclass
class Settings:
    host: str = "127.0.0.1"       # loopback only — never bind 0.0.0.0
    port: int = 8787
    mock_mode: bool = True         # start in mock mode: no real devices needed
    api_token: str = "dev-local-token"  # simple bearer for the local API
    db_path: str = str(CORE_ROOT / "data" / "orchestrator.db")
    media_dir: str = str(CORE_ROOT / "data" / "media")
    web_dir: str = str(REPO_ROOT / "web")
    # signing (free Apple ID) — used by signing/resign_wda.py
    apple_id: str = ""             # secondary Apple ID recommended
    wda_resign_days: int = 6       # re-sign before the 7-day cert expires
    # tunnel backend: "pymobiledevice3" or "go-ios"
    tunnel_backend: str = "pymobiledevice3"
    # media handoff to the phone (put_media step via a Shortcut)
    lan_host: str = ""             # Mac LAN IP the phone can reach; auto-detected if empty
    media_token: str = "change-me-media-token"   # unguessable path segment for /media
    shortcut_save_photos: str = "OrchSaveToPhotos"  # user-created Shortcut name
    # health/recovery loop
    health_interval_s: int = 10
    devices: list[DeviceConfig] = field(default_factory=list)


def _load_devices() -> list[DeviceConfig]:
    path = REPO_ROOT / "devices.json"
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [DeviceConfig(**d) for d in raw]
    # Mock defaults mirroring the target setup.
    return [
        DeviceConfig(udid="MOCK-15PM-0001", name="iPhone 15 Pro Max", ios="26",
                     wda_port=8100, mjpeg_port=9100, vpn_expected_region="US"),
        DeviceConfig(udid="MOCK-XSMAX-0002", name="iPhone XS Max", ios="18",
                     wda_port=8101, mjpeg_port=9101, vpn_expected_region="US"),
    ]


def _detect_lan_ip() -> str:
    """Best-effort local LAN IP (for phone->Mac media fetch). Never raises."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))          # no packet sent; just picks the iface
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def load_settings() -> Settings:
    s = Settings(
        host=os.getenv("ORCH_HOST", "127.0.0.1"),
        port=int(os.getenv("ORCH_PORT", "8787")),
        mock_mode=_bool("ORCH_MOCK", True),
        api_token=os.getenv("ORCH_TOKEN", "dev-local-token"),
        apple_id=os.getenv("ORCH_APPLE_ID", ""),
        tunnel_backend=os.getenv("ORCH_TUNNEL", "pymobiledevice3"),
        lan_host=os.getenv("ORCH_LAN_HOST", ""),
        media_token=os.getenv("ORCH_MEDIA_TOKEN", "change-me-media-token"),
        devices=_load_devices(),
    )
    if not s.lan_host:
        s.lan_host = _detect_lan_ip()
    Path(s.db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(s.media_dir).mkdir(parents=True, exist_ok=True)
    return s


settings = load_settings()
