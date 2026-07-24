"""Regression tests for .env parsing.

Real-world failure this guards against: `.env.example` documents options with
inline comments (`ORCH_LLM_MAX_PER_MIN=20      # rate limit`). A naive loader
passed the comment to int() and the ENTIRE app crashed at import time.
"""
import os

from core.config import (_bool, _int, _load_dotenv, _str,
                         _strip_inline_comment, _unquote)


def test_strip_inline_comment():
    assert _strip_inline_comment("20      # rate limit (calls/minute)") == "20      "
    assert _strip_inline_comment("127.0.0.1   # loopback only").strip() == "127.0.0.1"
    assert _strip_inline_comment("plain") == "plain"
    # a '#' that is not preceded by whitespace is DATA, not a comment
    assert _strip_inline_comment("pa#ssword") == "pa#ssword"
    # quoted '#' is data too
    assert _strip_inline_comment("\"a # b\"") == "\"a # b\""


def test_unquote():
    assert _unquote('"abc"') == "abc"
    assert _unquote("'abc'") == "abc"
    assert _unquote("  abc  ") == "abc"
    assert _unquote('"un"matched') == '"un"matched'


def test_int_and_bool_tolerate_comments(monkeypatch):
    monkeypatch.setenv("ORCH_T_INT", "20      # rate limit")
    assert _int("ORCH_T_INT", 5) == 20
    monkeypatch.setenv("ORCH_T_INT", "not-a-number")
    assert _int("ORCH_T_INT", 5) == 5          # falls back, never raises
    monkeypatch.delenv("ORCH_T_INT")
    assert _int("ORCH_T_INT", 7) == 7

    monkeypatch.setenv("ORCH_T_BOOL", "true    # yes really")
    assert _bool("ORCH_T_BOOL", False) is True
    monkeypatch.setenv("ORCH_T_BOOL", "false   # nope")
    assert _bool("ORCH_T_BOOL", True) is False


def test_str_strips_comment(monkeypatch):
    monkeypatch.setenv("ORCH_T_STR", "127.0.0.1   # loopback")
    assert _str("ORCH_T_STR") == "127.0.0.1"


def test_load_dotenv_handles_comments_and_export(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "# a comment line\n"
        "\n"
        "ORCH_ZZ_PORT=8787   # inline comment\n"
        "export ORCH_ZZ_NAME=\"quoted value\"\n"
        "ORCH_ZZ_EMPTY=\n"
    )
    for k in ("ORCH_ZZ_PORT", "ORCH_ZZ_NAME", "ORCH_ZZ_EMPTY"):
        monkeypatch.delenv(k, raising=False)
    _load_dotenv(env)
    assert os.environ["ORCH_ZZ_PORT"] == "8787"
    assert os.environ["ORCH_ZZ_NAME"] == "quoted value"
    assert os.environ["ORCH_ZZ_EMPTY"] == ""


def test_env_example_parses_cleanly(tmp_path, monkeypatch):
    """Every numeric key in .env.example must survive the loader + int()."""
    from pathlib import Path
    example = Path(__file__).resolve().parents[2] / ".env.example"
    assert example.exists()
    # load into a clean namespace, then verify the numeric ones
    for line in example.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        monkeypatch.setenv(key.strip(), _strip_inline_comment(val).strip())
    for key, default in (("ORCH_PORT", 8787), ("ORCH_LLM_MAX_PER_MIN", 20),
                         ("ORCH_WDA_RESIGN_DAYS", 6), ("ORCH_HEALTH_INTERVAL_S", 10)):
        assert isinstance(_int(key, default), int)
