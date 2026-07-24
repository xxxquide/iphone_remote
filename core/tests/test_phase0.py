import asyncio

from core.phase0 import (Check, Status, check_tool, ios_tooling_warning,
                         render, run_all, summarize)


def test_check_tool(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda c: "/usr/bin/" + c)
    assert check_tool("xcrun", "d", "fix").status == Status.PASS
    monkeypatch.setattr("shutil.which", lambda c: None)
    assert check_tool("xcrun", "d", "fix", required=True).status == Status.FAIL
    assert check_tool("ios", "d", "fix", required=False).status == Status.WARN


def test_check_tool_detects_installed_but_broken(tmp_path, monkeypatch):
    """A tool on PATH that CRASHES must FAIL (e.g. Appium on Node < 20.19)."""
    broken = tmp_path / "appium"
    broken.write_text("#!/bin/bash\necho 'TypeError: tracingChannel' >&2\nexit 1\n")
    broken.chmod(0o755)
    monkeypatch.setattr("shutil.which", lambda c: str(broken))
    chk = check_tool("appium", "Appium server", "fix", required=True, verify=["--version"])
    assert chk.status == Status.FAIL
    assert "FAILS to run" in chk.detail


def test_check_node_version(monkeypatch, tmp_path):
    from core.phase0 import check_node

    def fake_node(version: str):
        p = tmp_path / f"node{version}"
        p.write_text(f"#!/bin/bash\necho {version}\n")
        p.chmod(0o755)
        monkeypatch.setattr("shutil.which", lambda c: str(p))

    fake_node("v18.18.0")
    assert check_node().status == Status.FAIL      # too old for Appium 3
    fake_node("v22.12.0")
    assert check_node().status == Status.PASS


def test_ios_tooling_warning():
    assert ios_tooling_warning("26.5").status == Status.WARN
    assert ios_tooling_warning("26.4.1").status == Status.WARN
    assert ios_tooling_warning("26.2") is None
    assert ios_tooling_warning("18") is None


def test_summarize_exit_code():
    counts, code = summarize([Check("a", Status.PASS), Check("b", Status.FAIL)])
    assert counts[Status.FAIL] == 1 and code == 1
    _, ok = summarize([Check("a", Status.PASS), Check("b", Status.WARN)])
    assert ok == 0                       # warnings don't fail the gate


def test_run_all_mock():
    checks = asyncio.run(run_all())
    assert any(c.name.startswith("device:") and c.status == Status.PASS for c in checks)
    assert any(c.name.startswith("WDA:") and c.status == Status.SKIP for c in checks)
    assert "Phase 0 Doctor" in render(checks)
