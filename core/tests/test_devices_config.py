"""Regression tests for device-registry loading.

Two real failures this guards against:
  1. devices.json full of `REPLACE-WITH-REAL-UDID...` placeholders replaced the
     mock devices -> "assert 4 == 2" and "KeyError: unknown device MOCK-...".
  2. The doctor reported `PASS device: REPLACE-WITH-REAL-UDID-15PM`, i.e. a
     placeholder was treated as a configured device.
"""
import json

from core.config import PLACEHOLDER_UDID, _load_devices


def test_placeholder_devices_are_ignored(tmp_path, monkeypatch):
    import core.config as cfg
    devices_file = tmp_path / "devices.json"
    devices_file.write_text(json.dumps([
        {"udid": f"{PLACEHOLDER_UDID}-15PM", "name": "iPhone 15 Pro Max", "ios": "26"},
        {"udid": f"{PLACEHOLDER_UDID}-XSMAX", "name": "iPhone XS Max", "ios": "18"},
    ]))
    monkeypatch.setattr(cfg, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("ORCH_SKIP_DEVICES_FILE", raising=False)
    devs = _load_devices()
    # Falls back to the built-in mock devices instead of the placeholders.
    assert len(devs) == 2
    assert all(d.udid.startswith("MOCK-") for d in devs)


def test_real_devices_are_used(tmp_path, monkeypatch):
    import core.config as cfg
    (tmp_path / "devices.json").write_text(json.dumps([
        {"udid": "00008120-REAL", "name": "iPhone 15 Pro Max", "ios": "26.3",
         "point_w": 430, "point_h": 932},
    ]))
    monkeypatch.setattr(cfg, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("ORCH_SKIP_DEVICES_FILE", raising=False)
    devs = _load_devices()
    assert [d.udid for d in devs] == ["00008120-REAL"]
    assert devs[0].point_w == 430


def test_mixed_file_keeps_only_real(tmp_path, monkeypatch):
    import core.config as cfg
    (tmp_path / "devices.json").write_text(json.dumps([
        {"udid": f"{PLACEHOLDER_UDID}-XSMAX", "name": "iPhone XS Max", "ios": "18"},
        {"udid": "00008120-REAL", "name": "iPhone 15 Pro Max", "ios": "26.3"},
    ]))
    monkeypatch.setattr(cfg, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("ORCH_SKIP_DEVICES_FILE", raising=False)
    assert [d.udid for d in _load_devices()] == ["00008120-REAL"]


def test_tests_use_isolated_db():
    """conftest must redirect the DB, or tests mutate the developer's real data."""
    import os
    from core.config import settings
    assert os.environ.get("ORCH_DB")
    assert settings.db_path == os.environ["ORCH_DB"]
    assert "orch_test_" in settings.db_path
