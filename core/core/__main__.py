"""Entrypoint: python -m core

Starts the loopback API server (REST + WebSocket) and serves the browser
dashboard. In mock mode (default) it needs no real devices.
"""
from __future__ import annotations

import uvicorn

from .config import settings


def main() -> None:
    banner = (
        f"\n  iphone-orchestrator core v0.1\n"
        f"  mode:   {'MOCK' if settings.mock_mode else 'REAL DEVICES'}\n"
        f"  API:    http://{settings.host}:{settings.port}\n"
        f"  UI (B): http://{settings.host}:{settings.port}/  (browser dashboard)\n"
        f"  devices:{', '.join(d.name for d in settings.devices)}\n"
    )
    print(banner)
    uvicorn.run(
        "core.api:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
