import numpy as np
from PIL import Image

from core.vision.templates import match_template


def _write(path, arr):
    Image.fromarray(arr.astype("uint8")).save(path)


def test_match_template_finds_patch(tmp_path):
    # Scene: mid-gray with a TEXTURED 24x24 patch at (100,150).
    # (A constant patch has zero variance -> NCC undefined, so give it a gradient.)
    scene = np.full((300, 220), 90, dtype=np.uint8)
    grad = np.linspace(0, 255, 24, dtype=np.uint8)
    patch = np.tile(grad, (24, 1))            # horizontal gradient, real variance
    scene[150:174, 100:124] = patch
    tmpl = scene[150:174, 100:124].copy()
    sp, tp = tmp_path / "scene.png", tmp_path / "tmpl.png"
    _write(sp, scene)
    _write(tp, tmpl)

    m = match_template(str(sp), str(tp), threshold=0.5)
    assert m is not None
    # Expected center ~ (112, 162); numpy fallback downscales, allow tolerance.
    assert abs(m.x - 112) < 12 and abs(m.y - 162) < 12
    assert m.score > 0.5


def test_match_template_absent_returns_none(tmp_path):
    scene = np.full((120, 120), 100, dtype=np.uint8)
    tmpl = np.full((20, 20), 255, dtype=np.uint8)   # not present in flat scene
    sp, tp = tmp_path / "s.png", tmp_path / "t.png"
    _write(sp, scene); _write(tp, tmpl)
    assert match_template(str(sp), str(tp), threshold=0.9) is None
