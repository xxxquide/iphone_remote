import asyncio

from core.vision.ocr import OCRWord, find_text
from core.vision.targeting import Targeter, TargetSpec, _search_ax


def test_search_ax_finds_by_label():
    tree = {"type": "App", "children": [
        {"label": "Cancel", "rect": {"x": 0, "y": 0, "width": 10, "height": 10}},
        {"label": "Post", "rect": {"x": 100, "y": 200, "width": 40, "height": 20}},
    ]}
    node = _search_ax(tree, "post")
    assert node and node["rect"]["x"] == 100


def test_find_text_exact_then_substring():
    words = [OCRWord("Next step", 10, 20, 80, 30), OCRWord("Post", 0, 0, 40, 20)]
    assert find_text(words, "Post").x == 0
    assert find_text(words, "next").text == "Next step"      # substring, case-insensitive
    assert find_text(words, "missing") is None


def test_targeter_mock_returns_hit():
    # In mock mode Targeter short-circuits to xy (or a default).
    class _WDA:  # minimal stub
        pass
    t = Targeter(_WDA(), "MOCK", scale=3.0)
    hit = asyncio.run(t.find(TargetSpec(xy=(123, 456))))
    assert (hit.x, hit.y) == (123, 456)
    assert hit.via == "mock"
