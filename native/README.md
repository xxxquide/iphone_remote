# Native client (UI variation A)

SwiftUI menu-bar agent + main window. Talks to the local core service
(`http://127.0.0.1:8787`) — the same API the browser dashboard uses.

## Two ways to run

### 1. Quick (SwiftPM executable)
```bash
cd native
swift run           # opens a window; menu-bar item appears
```
Good for iterating on the UI. Note: menu-bar-only behaviour and TCC
entitlements need a real app bundle (below).

### 2. Real app (recommended for Phase 4+)
1. Xcode → New → macOS App (SwiftUI, "OrchestratorApp").
2. Add all files from `Sources/OrchestratorApp/` to the target.
3. Signing: your free Apple ID / personal team, **ad-hoc is fine** for personal use.
4. For a menu-bar-only agent set `LSUIElement = YES` in Info.plist.
5. Add these Info.plist usage strings:
   - **`NSCameraUsageDescription`** — REQUIRED for live-view. Capturing a
     connected iPhone via AVFoundation counts as camera access; without it the
     capture device delivers no frames. Approve the Camera prompt on first run.
   - `NSLocalNetworkUsageDescription` — talking to iPhones over Wi-Fi.
   - Screen Recording / Accessibility are granted in System Settings at first run.

## Live-view (implemented)
`LiveView.swift` shows the phone with the lowest-latency source available:
- **AVFoundation USB capture** — enables iOS devices as capture sources via
  CoreMediaIO (`enableDALDevices`), finds the device whose `uniqueID == udid`,
  renders an `AVCaptureVideoPreviewLayer`. Needs the iPhone connected by USB,
  unlocked, "Trust"ed, plus Camera permission.
- **MJPEG fallback** — if no capture device is found, it streams
  `/api/devices/{udid}/stream` from the core and renders the frames.
Clicks map to real device points using the core-provided logical screen size
(`point_w`/`point_h`), so taps land where you click.

## Still stubbed
- API token is hard-coded; move to Keychain in Phase 5.
- The core must be running (`cd ../core && python -m core`).
