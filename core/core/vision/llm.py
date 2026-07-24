"""Vision-LLM targeting (cascade level 4): screenshot + prompt -> coordinates.

Last-resort locator for when AX tree, OCR, and template matching all miss. Sends
the current screenshot plus a natural-language description ("the blue Post
button") to a vision model and parses back the CENTER pixel of the element.

Cost control is first-class:
  * TTLCache — identical (screenshot, description) lookups don't re-call the model
    (e.g. across step retries on an unchanged screen).
  * RateLimiter — a sliding-window cap on calls/minute; over budget -> return None
    (fast fallback) instead of spending a call or blocking the run.

Backends:
  * NullVisionLLM       — default (mock mode / no API key). Always None.
  * OpenAICompatibleVisionLLM — POSTs to any OpenAI-style /chat/completions vision
    endpoint. API key comes from settings (env/Keychain), never hardcoded.

Coordinates returned are image PIXELS; the Targeter divides by device scale to
get logical points (same contract as OCR/template).
"""
from __future__ import annotations

import base64
import collections
import hashlib
import json
import re
import time
from typing import Optional

import httpx

from ..config import settings

Coord = tuple[float, float]
_MISS = object()


# --------------------------------------------------------------------------- #
# Cost control
# --------------------------------------------------------------------------- #
class RateLimiter:
    """Sliding-window limiter: at most `max_calls` within `window_s` seconds."""

    def __init__(self, max_calls: int = 20, window_s: float = 60.0) -> None:
        self.max_calls = max_calls
        self.window_s = window_s
        self._calls: collections.deque[float] = collections.deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self._calls and now - self._calls[0] > self.window_s:
            self._calls.popleft()
        if len(self._calls) >= self.max_calls:
            return False
        self._calls.append(now)
        return True


class TTLCache:
    """Tiny LRU + TTL cache. Stores positive AND negative (None) results."""

    def __init__(self, maxsize: int = 128, ttl_s: float = 60.0) -> None:
        self.maxsize = maxsize
        self.ttl_s = ttl_s
        self._data: "collections.OrderedDict[str, tuple[object, float]]" = collections.OrderedDict()

    def get(self, key: str):
        item = self._data.get(key)
        if item is None:
            return _MISS
        value, ts = item
        if time.monotonic() - ts > self.ttl_s:
            self._data.pop(key, None)
            return _MISS
        self._data.move_to_end(key)
        return value

    def set(self, key: str, value) -> None:
        self._data[key] = (value, time.monotonic())
        self._data.move_to_end(key)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #
class VisionLLM:
    def available(self) -> bool:  # pragma: no cover - interface
        return False

    def locate(self, image_path: str, describe: str) -> Optional[Coord]:  # pragma: no cover
        return None


class NullVisionLLM(VisionLLM):
    def available(self) -> bool:
        return False

    def locate(self, image_path: str, describe: str) -> Optional[Coord]:
        return None


def parse_coords(text: str, w: int, h: int) -> Optional[Coord]:
    """Extract {x,y} pixels from a model reply; clamp to image bounds."""
    if not text:
        return None
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if obj.get("found") is False or "x" not in obj or "y" not in obj:
        return None
    try:
        x = float(obj["x"])
        y = float(obj["y"])
    except (TypeError, ValueError):
        return None
    return (min(max(x, 0.0), float(w)), min(max(y, 0.0), float(h)))


_PROMPT = (
    "You are a precise UI locator. The image is a phone screenshot, {w}x{h} pixels. "
    "Find the element described as: \"{desc}\". "
    "Respond with ONLY compact JSON and nothing else: "
    "{{\"x\": <int pixel>, \"y\": <int pixel>}} for the element's CENTER, "
    "or {{\"found\": false}} if it is not visible."
)


class OpenAICompatibleVisionLLM(VisionLLM):
    def __init__(self, base_url: str, model: str, api_key: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def locate(self, image_path: str, describe: str) -> Optional[Coord]:
        try:
            from PIL import Image
            with Image.open(image_path) as im:
                w, h = im.size
            b64 = base64.b64encode(open(image_path, "rb").read()).decode()
            payload = {
                "model": self.model,
                "temperature": 0,
                "max_tokens": 40,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT.format(w=w, h=h, desc=describe)},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }],
            }
            r = httpx.post(f"{self.base_url}/chat/completions",
                           headers={"Authorization": f"Bearer {self.api_key}"},
                           json=payload, timeout=self.timeout)
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
            return parse_coords(text, w, h)
        except Exception:
            return None


class CachingVisionLLM(VisionLLM):
    """Wraps a backend with a TTL cache and a rate limiter."""

    def __init__(self, backend: VisionLLM,
                 limiter: Optional[RateLimiter] = None,
                 cache: Optional[TTLCache] = None) -> None:
        self.backend = backend
        self.limiter = limiter or RateLimiter()
        self.cache = cache or TTLCache()

    def available(self) -> bool:
        return self.backend.available()

    def locate(self, image_path: str, describe: str) -> Optional[Coord]:
        if not self.backend.available():
            return None
        key = self._key(image_path, describe)
        cached = self.cache.get(key)
        if cached is not _MISS:
            return cached  # may be a positive coord or a cached None
        if not self.limiter.allow():
            return None    # over budget: fast fallback, do NOT cache
        result = self.backend.locate(image_path, describe)
        self.cache.set(key, result)
        return result

    @staticmethod
    def _key(image_path: str, describe: str) -> str:
        try:
            digest = hashlib.sha1(open(image_path, "rb").read()).hexdigest()[:16]
        except OSError:
            digest = image_path
        return f"{digest}|{describe.strip().lower()}"


def get_llm() -> VisionLLM:
    if settings.mock_mode or not settings.llm_enabled or not settings.llm_api_key:
        return NullVisionLLM()
    backend = OpenAICompatibleVisionLLM(settings.llm_base_url, settings.llm_model,
                                        settings.llm_api_key)
    return CachingVisionLLM(
        backend,
        RateLimiter(settings.llm_max_per_min, 60.0),
        TTLCache(settings.llm_cache_size, settings.llm_cache_ttl_s),
    )
