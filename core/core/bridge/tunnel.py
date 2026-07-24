"""iOS 17+ tunnel manager.

Since iOS 17 the developer-service front door moved to CoreDevice / RemoteXPC,
which requires a trusted tunnel before WDA/testmanagerd is reachable.

Backends:
  - pymobiledevice3:  sudo pymobiledevice3 remote tunneld       (root) OR
                      pymobiledevice3 ... --userspace           (no root)
  - go-ios:           sudo ios tunnel start [--userspace]

KNOWN ISSUE (verify on your build): go-ios userspace tunnel regressed on
iOS 26.5 (issue #772); works on 26.0-26.2. Prefer pymobiledevice3 tunneld,
or keep the 15 Pro Max on iOS 26.2-26.3. See docs/ARCHITECTURE.md.
"""
from __future__ import annotations

from ..config import settings
from .base import supervisor


async def start_tunnel() -> bool:
    """Start the shared tunnel daemon (one per host covers all devices)."""
    if settings.mock_mode:
        return True
    if settings.tunnel_backend == "go-ios":
        # NOTE: --userspace avoids root but is broken on iOS 26.5 (#772).
        argv = ["ios", "tunnel", "start", "--userspace"]
    else:
        # pymobiledevice3 tunneld multiplexes all attached devices.
        # Requires sudo for the TUN interface (or use --script-mode/userspace).
        argv = ["pymobiledevice3", "remote", "tunneld"]
    await supervisor.start("tunnel", argv)
    return supervisor.is_running("tunnel")


async def stop_tunnel() -> None:
    await supervisor.stop("tunnel")


def tunnel_up() -> bool:
    if settings.mock_mode:
        return True
    return supervisor.is_running("tunnel")


async def run_wda(udid: str) -> bool:
    """Launch WDA on a device (go-ios path). Preinstalled WDA recommended.

    Real flow: `ios runwda --udid=<udid>` after the tunnel is up, then forward
    the WDA + MJPEG ports to localhost. Kept as a supervised process.
    """
    if settings.mock_mode:
        return True
    await supervisor.start(f"wda:{udid}", ["ios", "runwda", f"--udid={udid}"])
    return supervisor.is_running(f"wda:{udid}")
