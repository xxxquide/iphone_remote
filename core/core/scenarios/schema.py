"""Scenario / Step data model. Scenarios are declarative YAML documents."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

SCENARIO_DIR = Path(__file__).resolve().parent


@dataclass
class Step:
    action: str                       # see engine.ACTIONS
    name: str = ""
    target: dict[str, Any] = field(default_factory=dict)   # -> TargetSpec
    value: Any = None                 # text to type, url, bundle id, ms to wait
    verify: dict[str, Any] = field(default_factory=dict)   # post-check target
    optional: bool = False            # e.g. permission dialogs
    manual: bool = False              # pause for human step-in
    always: bool = False              # re-run on resume (idempotent setup: vpn/wake/launch)
    retries: int = 2


@dataclass
class Scenario:
    name: str
    description: str = ""
    platform: str = ""
    steps: list[Step] = field(default_factory=list)

    @property
    def total_steps(self) -> int:
        return len(self.steps)


def load_scenario(name: str) -> Scenario:
    path = SCENARIO_DIR / f"{name}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = [Step(**s) for s in raw.get("steps", [])]
    return Scenario(name=raw["name"], description=raw.get("description", ""),
                    platform=raw.get("platform", ""), steps=steps)


def list_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIO_DIR.glob("*.yaml"))
