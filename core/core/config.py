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


def _strip_inline_comment(value: str) -> str:
    """Drop a trailing ` # comment` from a .env value.

    `.env.example` documents options inline (`ORCH_PORT=8787   # loopback only`),
    so a naive parser would hand `int()` the whole comment. Only an UNQUOTED `#`
    that follows whitespace starts a comment; `#` inside quotes is data, and a
    token like `pa#ss` stays intact.
    """
    quote = ""
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1].isspace()):
            return value[:i]
    return value


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines, `export` and inline comments ok)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), _unquote(_strip_inline_comment(val)))


if os.getenv("ORCH_SKIP_DOTENV", "").strip() not in {"1", "true", "yes"}:
    _load_dotenv(REPO_ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    raw = _strip_inline_comment(os.getenv(name, str(default))).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    """Tolerant int env read — never crashes the whole app on a stray comment."""
    raw = _strip_inline_comment(os.getenv(name, "")).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _str(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    return _unquote(_strip_inline_comment(raw)) if raw is not None else default


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
    point_w: float = 0.0           # logical screen width in points (for tap mapping)
    point_h: float = 0.0           # logical screen height in points


@dataclass
class Settings:
    host: str = "127.0.0.1"       # loopback only — never bind 0.0.0.0
    port: int = 8787
    mock_mode: bool = True         # start in mock mode: no real devices needed
    api_token: str = "dev-local-token"  # simple bearer for the local API
    db_path: str = str(CORE_ROOT / "data" / "orchestrator.db")  # override: ORCH_DB
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
    # vision-LLM targeting (cascade level 4)
    llm_enabled: bool = False
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""          # from ORCH_LLM_API_KEY (or Keychain); never hardcode
    llm_max_per_min: int = 20      # rate limit
    llm_cache_ttl_s: int = 60
    llm_cache_size: int = 128
    devices: list[DeviceConfig] = field(default_factory=list)


PLACEHOLDER_UDID = "REPLACE-WITH-REAL-UDID"


def _load_devices() -> list[DeviceConfig]:
    """Devices from devices.json, else built-in mock devices.

    Placeholder entries (the `REPLACE-WITH-REAL-UDID...` rows that ship in
    devices.json.example) are IGNORED: they are not real devices, and letting
    them through made the doctor report a bogus PASS and pushed the mock
    devices out of the registry. Run 4-real-mode.command to fill in real UDIDs.
    """
    path = REPO_ROOT / "devices.json"
    skip = os.getenv("ORCH_SKIP_DEVICES_FILE", "").strip() in {"1", "true", "yes"}
    if path.exists() and not skip:
        raw = json.loads(path.read_text(encoding="utf-8"))
        real = [d for d in raw if PLACEHOLDER_UDID not in str(d.get("udid", ""))]
        if real:
            return [DeviceConfig(**d) for d in real]
    # Mock defaults mirroring the target setup.
    return [
        DeviceConfig(udid="MOCK-15PM-0001", name="iPhone 15 Pro Max", ios="26",
                     wda_port=8100, mjpeg_port=9100, vpn_expected_region="US",
                     point_w=430, point_h=932),
        DeviceConfig(udid="MOCK-XSMAX-0002", name="iPhone XS Max", ios="18",
                     wda_port=8101, mjpeg_port=9101, vpn_expected_region="US",
                     point_w=414, point_h=896),
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
        host=_str("ORCH_HOST", "127.0.0.1"),
        port=_int("ORCH_PORT", 8787),
        mock_mode=_bool("ORCH_MOCK", True),
        api_token=_str("ORCH_TOKEN", "dev-local-token"),
        # Tests set ORCH_DB to an isolated file; without honouring it they ran
        # against the real database and saw leftover devices/tasks.
        db_path=_str("ORCH_DB", str(CORE_ROOT / "data" / "orchestrator.db")),
        media_dir=_str("ORCH_MEDIA_DIR", str(CORE_ROOT / "data" / "media")),
        apple_id=_str("ORCH_APPLE_ID", ""),
        tunnel_backend=_str("ORCH_TUNNEL", "pymobiledevice3"),
        lan_host=_str("ORCH_LAN_HOST", ""),
        media_token=_str("ORCH_MEDIA_TOKEN", "change-me-media-token"),
        llm_enabled=_bool("ORCH_LLM_ENABLED", False),
        llm_base_url=_str("ORCH_LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_model=_str("ORCH_LLM_MODEL", "gpt-4o-mini"),
        llm_api_key=_str("ORCH_LLM_API_KEY", ""),
        llm_max_per_min=_int("ORCH_LLM_MAX_PER_MIN", 20),
        wda_resign_days=_int("ORCH_WDA_RESIGN_DAYS", 6),
        health_interval_s=_int("ORCH_HEALTH_INTERVAL_S", 10),
        devices=_load_devices(),
    )
    if not s.lan_host:
        s.lan_host = _detect_lan_ip()
    Path(s.db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(s.media_dir).mkdir(parents=True, exist_ok=True)
    return s


settings = load_settings()
