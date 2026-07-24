from PIL import Image

from core.vision.llm import (CachingVisionLLM, NullVisionLLM, RateLimiter,
                             TTLCache, VisionLLM, get_llm, parse_coords)


def _img(tmp_path, name="s.png"):
    p = tmp_path / name
    Image.new("RGB", (300, 400), (10, 20, 30)).save(p)
    return str(p)


class FakeBackend(VisionLLM):
    def __init__(self, ret):
        self.ret = ret
        self.calls = 0

    def available(self):
        return True

    def locate(self, image_path, describe):
        self.calls += 1
        return self.ret


def test_rate_limiter():
    rl = RateLimiter(max_calls=2, window_s=100)
    assert rl.allow() and rl.allow()
    assert rl.allow() is False


def test_parse_coords():
    assert parse_coords('{"x": 100, "y": 200}', 300, 400) == (100.0, 200.0)
    assert parse_coords('sure: {"x":50,"y":60} ok', 300, 400) == (50.0, 60.0)
    assert parse_coords('{"found": false}', 300, 400) is None
    assert parse_coords("no json here", 300, 400) is None
    assert parse_coords('{"x": 9999, "y": -5}', 300, 400) == (300.0, 0.0)   # clamped


def test_caching_calls_backend_once(tmp_path):
    img = _img(tmp_path)
    be = FakeBackend((10, 20))
    llm = CachingVisionLLM(be, RateLimiter(10, 60), TTLCache(16, 60))
    assert llm.locate(img, "Post button") == (10, 20)
    assert llm.locate(img, "Post button") == (10, 20)
    assert be.calls == 1                       # second served from cache


def test_negative_result_is_cached(tmp_path):
    img = _img(tmp_path)
    be = FakeBackend(None)
    llm = CachingVisionLLM(be, RateLimiter(10, 60), TTLCache(16, 60))
    assert llm.locate(img, "x") is None
    assert llm.locate(img, "x") is None
    assert be.calls == 1


def test_rate_limited_skips_backend(tmp_path):
    img = _img(tmp_path)
    be = FakeBackend((1, 2))
    llm = CachingVisionLLM(be, RateLimiter(max_calls=0, window_s=60), TTLCache(16, 60))
    assert llm.locate(img, "x") is None
    assert be.calls == 0                       # over budget -> backend not called


def test_get_llm_null_in_mock():
    llm = get_llm()                            # mock mode in tests
    assert isinstance(llm, NullVisionLLM)
    assert llm.available() is False
