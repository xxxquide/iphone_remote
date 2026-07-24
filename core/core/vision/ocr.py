"""OCR backends for the targeting cascade (level 2).

Primary backend on macOS is Apple's Vision framework, exposed via a tiny Swift
helper CLI (tools/visionocr) that reads an image path and prints JSON words with
pixel bounding boxes. This keeps OCR fast, on-device, and dependency-free on the
Python side. A Null backend is used in mock mode / when the helper is absent.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from ..config import settings


@dataclass
class OCRWord:
    text: str
    x: float
    y: float
    w: float
    h: float
    conf: float = 1.0

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


class OCRBackend:
    def available(self) -> bool:  # pragma: no cover - interface
        return False

    def recognize(self, image_path: str) -> list[OCRWord]:  # pragma: no cover
        return []


class AppleVisionOCR(OCRBackend):
    """Invokes the `visionocr` Swift helper (see tools/visionocr/)."""

    def __init__(self, helper: str = "visionocr") -> None:
        self.helper = helper

    def available(self) -> bool:
        return shutil.which(self.helper) is not None

    def recognize(self, image_path: str) -> list[OCRWord]:
        try:
            res = subprocess.run([self.helper, image_path],
                                 capture_output=True, text=True, timeout=20)
        except Exception:
            return []
        if res.returncode != 0 or not res.stdout.strip():
            return []
        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError:
            return []
        return [OCRWord(text=d["text"], x=d["x"], y=d["y"], w=d["w"],
                        h=d["h"], conf=d.get("conf", 1.0)) for d in data]


class NullOCR(OCRBackend):
    def available(self) -> bool:
        return False

    def recognize(self, image_path: str) -> list[OCRWord]:
        return []


def get_ocr() -> OCRBackend:
    if settings.mock_mode:
        return NullOCR()
    v = AppleVisionOCR()
    return v if v.available() else NullOCR()


def find_text(words: list[OCRWord], needle: str) -> Optional[OCRWord]:
    """Locate a word: exact (case-insensitive) first, then substring."""
    n = needle.strip().lower()
    if not n:
        return None
    for w in words:
        if w.text.strip().lower() == n:
            return w
    for w in words:
        if n in w.text.strip().lower():
            return w
    return None
