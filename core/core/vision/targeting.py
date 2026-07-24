"""Targeting cascade: resolve a scenario target to screen coordinates (POINTS).

Order (fast/precise -> robust):
  1) AX tree   — WDA source(); match by label. Rect is already in points.
  2) OCR       — Apple Vision on a fresh screenshot; pixel centroid -> points.
  3) Template  — icon image match on the screenshot; pixel center -> points.
  4) xy        — explicit coordinate (points), as authored.
  5) LLM       — vision model hint (still a hook; Phase 4+).

Screenshots are in pixels (@3x); WDA taps use logical points, so OCR/template
hits are divided by the device scale. Every hit carries a via + confidence so
the engine can log how a target was found and run a post-check.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from ..bridge.wda import WDAClient
from ..config import settings
from . import llm as llm_mod
from . import ocr as ocr_mod
from . import templates as tmpl_mod

# async screenshotter(udid) -> path|None
Screenshotter = Callable[[str], Awaitable[Optional[str]]]


@dataclass
class TargetSpec:
    ax_label: Optional[str] = None
    text: Optional[str] = None
    template: Optional[str] = None
    xy: Optional[tuple[float, float]] = None
    describe: Optional[str] = None


@dataclass
class Hit:
    x: float          # logical points
    y: float
    via: str
    confidence: float


class Targeter:
    def __init__(self, wda: WDAClient, udid: str, scale: float = 3.0,
                 screenshotter: Optional[Screenshotter] = None,
                 ocr: Optional[ocr_mod.OCRBackend] = None,
                 llm: Optional[llm_mod.VisionLLM] = None) -> None:
        self.wda = wda
        self.udid = udid
        self.scale = scale or 1.0
        self.screenshotter = screenshotter
        self.ocr = ocr or ocr_mod.get_ocr()
        self.llm = llm or llm_mod.get_llm()
        self._shot_cache: Optional[str] = None

    async def find(self, spec: TargetSpec) -> Optional[Hit]:
        if settings.mock_mode:
            x, y = spec.xy if spec.xy else (200.0, 400.0)
            return Hit(x, y, "mock", 1.0)

        if spec.ax_label:
            hit = await self._via_ax(spec.ax_label)
            if hit:
                return hit
        if spec.text:
            hit = await self._via_ocr(spec.text)
            if hit:
                return hit
        if spec.template:
            hit = await self._via_template(spec.template)
            if hit:
                return hit
        if spec.xy:
            return Hit(spec.xy[0], spec.xy[1], "xy", 0.5)
        if spec.describe:
            return await self._via_llm(spec.describe)
        return None

    async def _screenshot(self) -> Optional[str]:
        if self._shot_cache:
            return self._shot_cache
        if self.screenshotter:
            self._shot_cache = await self.screenshotter(self.udid)
        return self._shot_cache

    def invalidate(self) -> None:
        """Call after an action changes the screen so OCR/template re-capture."""
        self._shot_cache = None

    async def _via_ax(self, label: str) -> Optional[Hit]:
        tree = await self.wda.source()
        node = _search_ax(tree.get("value", {}), label)
        if node and isinstance(node.get("rect"), dict):
            r = node["rect"]
            return Hit(r["x"] + r["width"] / 2, r["y"] + r["height"] / 2, "ax", 0.95)
        return None

    async def _via_ocr(self, text: str) -> Optional[Hit]:
        shot = await self._screenshot()
        if not shot or not self.ocr.available():
            return None
        word = ocr_mod.find_text(self.ocr.recognize(shot), text)
        if not word:
            return None
        return Hit(word.cx / self.scale, word.cy / self.scale, "ocr", word.conf)

    async def _via_template(self, template_path: str) -> Optional[Hit]:
        shot = await self._screenshot()
        if not shot:
            return None
        m = tmpl_mod.match_template(shot, template_path)
        if not m:
            return None
        return Hit(m.x / self.scale, m.y / self.scale, "template", m.score)

    async def _via_llm(self, describe: str) -> Optional[Hit]:
        if not self.llm.available():
            return None
        shot = await self._screenshot()
        if not shot:
            return None
        # Vision-LLM call is sync/blocking; run it off the event loop.
        coord = await asyncio.to_thread(self.llm.locate, shot, describe)
        if not coord:
            return None
        return Hit(coord[0] / self.scale, coord[1] / self.scale, "llm", 0.6)


def _search_ax(node: Any, label: str) -> Optional[dict]:
    if not isinstance(node, dict):
        return None
    hay = f"{node.get('label','')} {node.get('name','')} {node.get('value','')}".lower()
    if label.lower() in hay:
        return node
    for child in node.get("children", []) or []:
        found = _search_ax(child, label)
        if found:
            return found
    return None
