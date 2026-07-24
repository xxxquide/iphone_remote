"""Local API: REST + WebSocket + static browser dashboard.

Binds to loopback only. Both UIs (native app, browser) use this one contract.
Auth: a simple bearer token (settings.api_token) — fine for localhost/LAN.
"""
from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import health, vpn
from .bridge import devicectl, streaming, tunnel
from .bridge.wda import client_for
from .config import settings
from .events import bus
from .models import (LaunchRequest, OpenURLRequest, ScenarioRunRequest,
                     TapRequest, TypeRequest)
from .scenarios.schema import list_scenarios
from .scheduler import scheduler
from .store import store

from . import __version__

app = FastAPI(title="iphone-orchestrator core", version=__version__)


def auth(authorization: str = Header(default="")) -> None:
    token = authorization.replace("Bearer ", "").strip()
    if token != settings.api_token:
        raise HTTPException(status_code=401, detail="bad token")


@app.on_event("startup")
async def _startup() -> None:
    await store.open()
    for d in settings.devices:
        await store.upsert_device({
            "udid": d.udid, "name": d.name, "ios": d.ios,
            "status": "online" if settings.mock_mode else "unknown",
            "wda": "ready" if settings.mock_mode else "down",
            "tunnel": "up" if settings.mock_mode else "down",
            "ip": None, "vpn_region": d.vpn_expected_region, "profile_days_left": None,
        })
    scheduler.start()
    await scheduler.recover()                 # re-queue unfinished tasks after a restart
    asyncio.create_task(health.run_loop())    # heartbeats (mock) + recovery (real)


@app.on_event("shutdown")
async def _shutdown() -> None:
    await scheduler.stop()
    await store.close()


# ---- health & devices -------------------------------------------------------
@app.get("/api/health")
async def health_check() -> dict:
    return {"ok": True, "mock": settings.mock_mode, "version": app.version}


@app.get("/api/devices", dependencies=[Depends(auth)])
async def get_devices() -> list[dict]:
    return await store.list_devices()


@app.post("/api/devices/{udid}/tap", dependencies=[Depends(auth)])
async def tap(udid: str, req: TapRequest) -> dict:
    await client_for(udid).tap(req.x, req.y)
    await bus.emit("device.action", udid=udid, action="tap", x=req.x, y=req.y)
    return {"ok": True}


@app.post("/api/devices/{udid}/type", dependencies=[Depends(auth)])
async def type_text(udid: str, req: TypeRequest) -> dict:
    await client_for(udid).type_text(req.text)
    return {"ok": True}


@app.post("/api/devices/{udid}/launch", dependencies=[Depends(auth)])
async def launch(udid: str, req: LaunchRequest) -> dict:
    await devicectl.launch_app(udid, req.bundle_id)
    return {"ok": True}


@app.post("/api/devices/{udid}/open-url", dependencies=[Depends(auth)])
async def open_url(udid: str, req: OpenURLRequest) -> dict:
    await devicectl.open_url(udid, req.url)
    return {"ok": True}


@app.get("/api/devices/{udid}/stream")
async def stream(udid: str):
    """MJPEG passthrough for the browser <img>. Mock -> 204 (canvas fallback)."""
    if settings.mock_mode:
        return JSONResponse({"mock": True, "hint": "dashboard draws a mock canvas"},
                            status_code=204)
    return StreamingResponse(streaming.proxy_mjpeg(udid),
                             media_type="multipart/x-mixed-replace; boundary=--BoundaryString")


@app.post("/api/devices/{udid}/vpn/verify", dependencies=[Depends(auth)])
async def vpn_verify(udid: str) -> dict:
    dev = next((d for d in settings.devices if d.udid == udid), None)
    st = await vpn.verify_ip(udid, dev.vpn_expected_region if dev else "")
    return {"connected": st.connected, "ip": st.ip, "region": st.region}


# ---- scenarios & tasks ------------------------------------------------------
@app.get("/api/scenarios", dependencies=[Depends(auth)])
async def scenarios() -> list[str]:
    return list_scenarios()


@app.post("/api/scenarios/{name}/run", dependencies=[Depends(auth)])
async def run_scenario(name: str, req: ScenarioRunRequest) -> dict:
    task_id = await scheduler.enqueue(name, req.udid, req.params)
    return {"task_id": task_id}


@app.get("/api/tasks/{task_id}", dependencies=[Depends(auth)])
async def get_task(task_id: str) -> dict:
    task = await store.get_task(task_id)
    if not task:
        raise HTTPException(404, "no such task")
    return task


# ---- signing ----------------------------------------------------------------
@app.post("/api/devices/{udid}/resign-wda", dependencies=[Depends(auth)])
async def resign(udid: str) -> dict:
    from .signing.resign_wda import resign as do_resign
    return {"ok": do_resign(udid)}


# ---- websocket --------------------------------------------------------------
@app.websocket("/ws")
async def ws(ws: WebSocket) -> None:
    await ws.accept()
    q = bus.subscribe()
    try:
        await ws.send_json({"type": "hello", "mock": settings.mock_mode})
        while True:
            evt = await q.get()
            await ws.send_json(evt)
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(q)


# ---- media handoff to the phone (put_media Shortcut fetches this) -----------
@app.get("/media/{token}/{name}")
async def media(token: str, name: str):
    """Unauthenticated but token-gated: the phone's Shortcut can't send a bearer.
    For a real device the API must be LAN-reachable (bind ORCH_HOST=0.0.0.0)."""
    if token != settings.media_token:
        raise HTTPException(404, "not found")
    base = Path(settings.media_dir).resolve()
    p = (base / name).resolve()
    if not str(p).startswith(str(base)) or not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(str(p))


# ---- static browser dashboard (UI variation B) ------------------------------
_web = Path(settings.web_dir)
if _web.exists():
    app.mount("/", StaticFiles(directory=str(_web), html=True), name="web")
