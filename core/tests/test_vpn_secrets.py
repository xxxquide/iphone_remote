from core.vpn import extract_ip, note_run, state_for
from core import secrets


def test_extract_ip():
    assert extract_ip("Your IP is 203.0.113.42 today") == "203.0.113.42"
    assert extract_ip("no ip here") is None
    assert extract_ip("bad 999.999.1.1 addr") is None


def test_rotation_policy():
    st = state_for("DEV-ROT")
    st.runs_since_rotation = 0
    results = [note_run("DEV-ROT", rotate_every=3) for _ in range(3)]
    assert results == [False, False, True]           # rotate due on the 3rd run


def test_keychain_argv_construction():
    add = secrets._add_argv("tiktok", "acct1", "s3cret")
    assert add[:2] == ["security", "add-generic-password"]
    assert "com.orchestrator.tiktok" in add and "acct1" in add and "s3cret" in add
    get = secrets._get_argv("tiktok", "acct1")
    assert get[-1] == "-w" and "find-generic-password" in get
