"""End-to-end API test via httpx ASGITransport with manual lifespan.

Deliberately avoids Starlette's TestClient (its anyio portal + background tasks
can hang teardown in some sandboxes). Everything runs in one asyncio loop.

Run with:  python -m pytest tests   (NOT bare `pytest`, which can resolve to a
different interpreter, e.g. a conda base env, that lacks the venv's deps).
"""
import asyncio

import httpx
from httpx import ASGITransport

from core import api as api_mod
from core.config import settings

H = {"Authorization": f"Bearer {settings.api_token}"}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=api_mod.app),
                             base_url="http://test")


def test_end_to_end_mock():
    async def scenario() -> None:
        await api_mod._startup()
        try:
            async with _client() as c:
                assert (await c.get("/api/health")).json()["mock"] is True
                assert (await c.get("/api/devices")).status_code == 401   # auth enforced
                devices = (await c.get("/api/devices", headers=H)).json()
                assert len(devices) == 2
                assert devices[0]["point_w"] and devices[0]["point_h"]    # tap-mapping size
                udid = devices[0]["udid"]
                assert "tiktok_upload" in (await c.get("/api/scenarios", headers=H)).json()

                run = await c.post("/api/scenarios/tiktok_upload/run", headers=H,
                                   json={"udid": udid,
                                         "params": {"media_path": "/tmp/v.mp4",
                                                    "caption": "hi #fyp"}})
                task_id = run.json()["task_id"]

                state = ""
                for _ in range(100):
                    state = (await c.get(f"/api/tasks/{task_id}", headers=H)).json()["state"]
                    if state in ("done", "failed"):
                        break
                    await asyncio.sleep(0.05)
                assert state == "done"
        finally:
            await api_mod._shutdown()

    asyncio.run(scenario())


def test_media_token_gate():
    async def scenario() -> None:
        await api_mod._startup()
        try:
            async with _client() as c:
                assert (await c.get("/media/wrong-token/x.mp4")).status_code == 404
        finally:
            await api_mod._shutdown()

    asyncio.run(scenario())
