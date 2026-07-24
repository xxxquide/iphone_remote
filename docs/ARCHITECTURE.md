# Architecture (v2, condensed)

One **headless core service** on the Mac, two thin UIs over one loopback API.

```
Native app (SwiftUI) ─┐
                       ├─ REST + WebSocket @ 127.0.0.1:8787 ─ Core service ─ Device Bridge ─ USB/Wi-Fi ─ 2× iPhone
Browser dashboard  ───┘                                        │
                                                               ├ Scenario Engine (declarative steps, auto/manual)
                                                               ├ Targeting/Vision (AX → OCR → template → LLM)
                                                               ├ Scheduler/Queue (SQLite, retry, idempotency)
                                                               ├ Signing Manager (weekly WDA re-sign, free ID)
                                                               ├ VPN/Network (per-iPhone IP verify + rotation)
                                                               └ Store (SQLite) · Keychain · media on disk
```

## Why a headless core + two clients
The requirement is "both native and browser UI". Keeping all state and logic in
one engine means the two front-ends are thin views over the same API — no
duplicated logic, and adding a device or a third client never touches the core.

## Device Bridge (wrap, don't reinvent)
- `devicectl` — Apple's sanctioned lever: install/launch/openURL/screenshot/notify (USB or Wi-Fi). No paid account needed.
- **WebDriverAgent** — tap/type/element-tree/MJPEG. The only signed component (see SIGNING.md).
- `pymobiledevice3` — iOS 17+ tunnel + HEVC screen stream. Preferred tunnel.
- `go-ios` — alternative tunnel / runwda. ⚠ userspace tunnel broken on iOS 26.5 (#772); OK on 26.0–26.2.

## Hard blockers we design around (confirmed)
- A normal iOS app **cannot drive another app's UI** → all TikTok automation runs **from the Mac via WDA**, not from an on-device companion (we don't build one in v1).
- **No persistent iOS background process** → the brain + scheduler live on the Mac.
- iPhone Mirroring is human-only / one-device-at-a-time → we stream ourselves.

## Live-view
- Native: AVFoundation USB capture (lowest latency) — Phase 1.
- Browser: MJPEG passthrough from WDA (`/api/devices/{udid}/stream`).
- Alternative: pymobiledevice3 HEVC (`core-device display serve-web`).

## Open sub-problem: video into Photos
TikTok's picker reads from Photos/Files. `devicectl` doesn't put files into
Photos directly. Options to validate in Phase 0:
1. A Shortcut "save to Photos" triggered via `devicectl ... openURL` (shortcuts://).
2. iCloud Photos / Files sync from the Mac.
3. A tiny on-device helper with a "save media" App Intent (costs a signing slot).

## Compliance boundary
Local device orchestration is legitimate. Mass multi-account posting + IP
rotation "to avoid detection" violates TikTok ToS. This repo implements the
mechanism (dual-use); it does not implement detection evasion. For pure
scheduling of your own content, prefer TikTok's official Content Posting API.

## Versioning note
macOS 26 "Tahoe" / iOS 26 shipped Sept 2025 (mature). iOS/macOS 27 "Golden Gate"
are beta in mid-2026 — do not target them yet. Keep the 15 Pro Max on iOS
26.2–26.3 for smoother tooling.
