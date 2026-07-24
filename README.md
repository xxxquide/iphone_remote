# iphone-orchestrator

Local orchestrator for controlling & automating your own iPhones from one Mac —
live-view, scenario-driven video upload (TikTok first), a "see the buttons"
vision layer, and manual↔automatic control. Fully local, no cloud, no paid
Apple Developer account. Starter skeleton for **architecture v2**.

> **Setup:** MacBook M2 · macOS 26 · iPhone 15 Pro Max (iOS 26) + iPhone XS Max (iOS 18).

## What's here

```
iphone-orchestrator/
├── core/                 # headless engine: local REST+WS API, device bridge, scenarios
│   ├── core/             # python package (run: python -m core)
│   │   ├── api.py            # FastAPI: REST + WebSocket + serves the dashboard
│   │   ├── config.py         # settings (.env), device registry, MOCK mode
│   │   ├── store.py          # SQLite (devices/tasks/events)
│   │   ├── scheduler.py      # in-process queue: retry + idempotency
│   │   ├── bridge/           # devicectl · WDA · tunnel · streaming wrappers
│   │   ├── vision/           # targeting cascade: AX → OCR → template → LLM
│   │   ├── signing/          # free-account WDA weekly auto re-sign
│   │   ├── scenarios/        # engine + tiktok_upload.yaml
│   │   └── vpn.py            # per-iPhone IP verify + rotation policy
│   └── scripts/          # resign_wda.sh · phase0_smoke.sh
├── web/                  # UI variation B — browser dashboard (no build step)
├── native/              # UI variation A — SwiftUI menu-bar app (skeleton)
└── docs/                # ARCHITECTURE · PHASE0 · SIGNING
```

Both UIs talk to the **one** core API on `127.0.0.1:8787`, so logic lives in a
single engine and is never duplicated.

## Quick start (mock mode — no phones needed)

```bash
cd core
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m core
```
Open **http://127.0.0.1:8787/** → two mock devices, a live WebSocket feed, a
client-side "MOCK LIVE-VIEW", and the TikTok scenario you can enqueue end-to-end
(it runs as a dry-run in mock mode). This validates the whole architecture before
any real device is attached.

Native client:
```bash
cd native && swift run          # window + menu-bar item; talks to the running core
```

## Going real

1. Do **`docs/PHASE0.md`** on both phones (Developer Mode, trust, DDI, sign WDA once).
2. `cp devices.json.example devices.json` and fill in real UDIDs.
3. `cp .env.example .env` and set `ORCH_MOCK=false`.
4. `python -m core` — the Device Bridge now drives real devices.

## Status: what's real vs stubbed  (v0.3.0)
- **Real & runnable (tested in mock, `19 passed`):** core API (REST+WS), event bus,
  SQLite store, scheduler with idempotency **+ restart re-queue of unfinished tasks**,
  scenario engine + YAML, browser dashboard, mock devices/live-view, health/recovery
  loop, bridge command construction.
- **Implemented (need real device / macOS to exercise):** targeting cascade —
  **OCR** via an Apple Vision Swift helper (`tools/visionocr`) + **template matching**
  (OpenCV or numpy fallback); **put_media** (video→Photos via a Shortcut + LAN media
  route); **VPN IP verification** (ipify + OCR); **Keychain** secrets (`security`);
  weekly **WDA re-sign** orchestration; **native live-view** — AVFoundation USB
  capture (CoreMediaIO) with **MJPEG fallback** and click-to-tap mapped to real
  device points; **vision-LLM targeting** (cascade level 4) — screenshot+prompt →
  coordinates, with TTL cache + rate limit (off unless `ORCH_LLM_ENABLED`+key).
- **Still stubbed (clear TODOs):** true mid-step task resume, Keychain-backed API
  token in the native app.

## Tests
```bash
cd core && pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q          # 13 passed — scenarios, targeting, templates, vpn, secrets, API e2e
```

## Safety / compliance
This tool automates **your own** devices. Mass multi-account posting + IP rotation
to evade detection violates TikTok's ToS and risks bans — the repo implements the
mechanism (dual-use), **not** detection evasion. For scheduling your own content,
prefer TikTok's official Content Posting API. See `docs/ARCHITECTURE.md`.

## Language note
The engine is Python here for fastest time-to-first-run (pymobiledevice3 is
Python-native). The API contract is language-agnostic, so the engine can be
ported to Swift/Go later without touching either UI.
