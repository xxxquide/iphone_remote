# visionocr

Tiny macOS CLI that OCRs an image with Apple's **Vision** framework and prints
JSON words with pixel bounding boxes. The Python targeting cascade
(`core/core/vision/ocr.py`) calls it as a subprocess.

```bash
cd tools/visionocr
swift build -c release
cp .build/release/visionocr /usr/local/bin/      # or anywhere on PATH
visionocr /tmp/orch_shot.png
# -> [{"text":"Next","x":812.0,"y":120.0,"w":90.0,"h":34.0,"conf":0.99}, ...]
```

Notes
- Coordinates are in image **pixels**, top-left origin. The Python side divides
  by the device scale (@3x) to get logical points for WDA taps.
- No paid Apple account needed — it's a plain local CLI.
- If `visionocr` is not on PATH, `ocr.py` falls back to a Null backend and the
  cascade skips OCR (AX / template / xy still work).
