import time

from fastapi.testclient import TestClient

from core.api import app
from core.config import settings

H = {"Authorization": f"Bearer {settings.api_token}"}


def test_end_to_end_mock():
    with TestClient(app) as c:
        assert c.get("/api/health").json()["mock"] is True

        # auth is enforced
        assert c.get("/api/devices").status_code == 401
        devices = c.get("/api/devices", headers=H).json()
        assert len(devices) == 2
        udid = devices[0]["udid"]
        # logical screen size is exposed for native tap mapping
        assert devices[0]["point_w"] and devices[0]["point_h"]

        assert "tiktok_upload" in c.get("/api/scenarios", headers=H).json()

        run = c.post("/api/scenarios/tiktok_upload/run", headers=H,
                     json={"udid": udid, "params": {"media_path": "/tmp/v.mp4",
                                                     "caption": "hi #fyp"}})
        task_id = run.json()["task_id"]

        # let the scheduler finish the mock run
        state = ""
        for _ in range(50):
            state = c.get(f"/api/tasks/{task_id}", headers=H).json()["state"]
            if state in ("done", "failed"):
                break
            time.sleep(0.1)
        assert state == "done"


def test_media_token_gate():
    with TestClient(app) as c:
        assert c.get("/media/wrong-token/x.mp4").status_code == 404
