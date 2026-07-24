import os
import sys
import tempfile
from pathlib import Path

# Force mock mode + an isolated DB BEFORE core.config is imported anywhere.
os.environ.setdefault("ORCH_MOCK", "true")
os.environ.setdefault("ORCH_PORT", "8799")
os.environ["ORCH_DB"] = str(Path(tempfile.gettempdir()) / "orch_test.db")

# Make the `core` package importable when running from the repo `core/` dir.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
