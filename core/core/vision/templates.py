"""Template matching for the targeting cascade (level 3): find an icon on screen.

Backend priority:
  1) OpenCV cv2.matchTemplate (fast; `pip install opencv-python-headless`)
  2) numpy vectorized NCC fallback (downscales the scene to stay tractable)

Coordinates returned are the CENTER of the match in ORIGINAL scene pixels.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image


@dataclass
class Match:
    x: float          # center, original scene pixels
    y: float
    score: float


def _gray(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L"), dtype=np.float64)


def match_template(scene_path: str, template_path: str,
                   threshold: float = 0.75) -> Optional[Match]:
    scene = _gray(scene_path)
    tmpl = _gray(template_path)
    try:
        import cv2  # type: ignore
        return _match_cv2(scene, tmpl, threshold, cv2)
    except ImportError:
        return _match_numpy(scene, tmpl, threshold)


def _match_cv2(scene: np.ndarray, tmpl: np.ndarray, threshold: float, cv2) -> Optional[Match]:
    res = cv2.matchTemplate(scene.astype("float32"), tmpl.astype("float32"),
                            cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val < threshold:
        return None
    th, tw = tmpl.shape
    return Match(max_loc[0] + tw / 2, max_loc[1] + th / 2, float(max_val))


def _match_numpy(scene: np.ndarray, tmpl: np.ndarray, threshold: float,
                 max_scene_dim: int = 640) -> Optional[Match]:
    from numpy.lib.stride_tricks import sliding_window_view

    scale = 1.0
    big = max(scene.shape)
    if big > max_scene_dim:
        scale = max_scene_dim / big
        scene = _resize(scene, scale)
        tmpl = _resize(tmpl, scale)

    th, tw = tmpl.shape
    if th > scene.shape[0] or tw > scene.shape[1] or th < 2 or tw < 2:
        return None

    t = tmpl - tmpl.mean()
    tnorm = float(np.sqrt((t * t).sum()))
    if tnorm == 0:
        return None

    windows = sliding_window_view(scene, (th, tw))          # (Y, X, th, tw)
    w = windows - windows.mean(axis=(2, 3), keepdims=True)
    num = (w * t).sum(axis=(2, 3))
    denom = np.sqrt((w * w).sum(axis=(2, 3))) * tnorm
    ncc = np.zeros_like(num)
    np.divide(num, denom, out=ncc, where=denom > 0)

    y, x = np.unravel_index(int(np.argmax(ncc)), ncc.shape)
    score = float(ncc[y, x])
    if score < threshold:
        return None
    cx = (x + tw / 2) / scale
    cy = (y + th / 2) / scale
    return Match(cx, cy, score)


def _resize(arr: np.ndarray, scale: float) -> np.ndarray:
    img = Image.fromarray(arr.astype("uint8"))
    nw = max(1, int(arr.shape[1] * scale))
    nh = max(1, int(arr.shape[0] * scale))
    return np.asarray(img.resize((nw, nh), Image.BILINEAR), dtype=np.float64)
