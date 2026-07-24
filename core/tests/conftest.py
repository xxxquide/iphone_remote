"""Test bootstrap — must run BEFORE core.config is imported anywhere.

Hermetic by design: the suite previously picked up the developer's real
database, real .env and real devices.json, so results depended on local state
(e.g. "assert 4 == 2" once devices.json held placeholder rows). We now force
mock mode, an isolated per-run DB, and ignore local config files.
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = CORE_DIR.parent

# 1) Never read the developer's .env / devices.json during tests.
os.environ["ORCH_SKIP_DOTENV"] = "1"
os.environ["ORCH_SKIP_DEVICES_FILE"] = "1"

# 2) Force mock mode and a throwaway database + media dir per run.
_run = uuid.uuid4().hex[:8]
_tmp = Path(tempfile.gettempdir()) / f"orch_test_{_run}"
_tmp.mkdir(parents=True, exist_ok=True)
os.environ["ORCH_MOCK"] = "true"
os.environ["ORCH_PORT"] = "8799"
os.environ["ORCH_TOKEN"] = "dev-local-token"
os.environ["ORCH_DB"] = str(_tmp / "orchestrator.db")
os.environ["ORCH_MEDIA_DIR"] = str(_tmp / "media")

# 3) Make the `core` package importable when running from the repo `core/` dir.
sys.path.insert(0, str(CORE_DIR))
