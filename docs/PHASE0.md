# Phase 0 — prove the primitives (on your 2 phones)

Goal: before building anything, confirm you can live-view and script a tap on
**both** phones from the Mac, know which tunnel works on your iOS 26.x, and can
get a video onto the device.

## 0. Install tooling
```bash
xcode-select --install                       # + Xcode 26 from the App Store
brew install node go python@3.13 ffmpeg
npm i -g appium
appium driver install xcuitest               # v12.x (needs Appium 3)
brew install go-ios
python3 -m pip install -U pymobiledevice3
```

## 1. Prepare each phone (USB)
- Settings → Privacy & Security → **Developer Mode** = On (reboot).
- Connect USB → **Trust This Computer**.
- `xcrun devicectl list devices`  → both UDIDs listed. **PASS/FAIL**
- `pymobiledevice3 mounter auto-mount`  → DDI mounted.

## 2. Sign WDA once (Xcode GUI — free Apple ID)
```bash
appium driver run xcuitest open-wda
```
In Xcode: Automatically manage signing → your (secondary) Team → pick device →
**Product ▸ Test**. On the phone: Settings → General → VPN & Device Management →
**Trust**. Export the Apple Development cert from Keychain as `.p12` (see SIGNING.md).

## 3. Sanctioned Mac→iPhone ops
```bash
bash core/scripts/phase0_smoke.sh <UDID>
```
Expect: screenshot saved, openURL works, TikTok bundle id confirmed.

## 4. Tunnel + live-view + one tap
```bash
sudo pymobiledevice3 remote tunneld &                        # tunnel (root)
pymobiledevice3 core-device display serve-web --device <UDID># HEVC live-view in browser
# Appium session {automationName: XCUITest, udid, usePreinstalledWDA: true}
#   -> activateApp com.zhiliaoapp.musically -> one tap on "+"
```

## 5. Video into Photos (open sub-problem)
Try a Shortcut "Save to Photos" invoked via `devicectl ... openURL shortcuts://...`.
Measure reliability; compare with iCloud/Files. Record what worked.

## Pass criteria (both phones)
- [ ] live-view visible
- [ ] `openURL` + screenshot from Mac
- [ ] programmatic tap in TikTok via WDA
- [ ] known-good tunnel on your iOS 26.x (watch go-ios #772 on 26.5)
- [ ] a video can be placed into Photos

## Known workarounds
- **Xcode 26 provisioning bug (#2850):** sign WDA via GUI once, then `usePreinstalledWDA: true`.
- **go-ios tunnel on 26.5 (#772):** use `pymobiledevice3 remote tunneld` or Appium `appium-ios-remotexpc`; or stay on 26.2–26.3.
- **WDA won't launch / "message:5":** cert expired or app not trusted → re-sign (SIGNING.md) + re-Trust.
- **WDA needs unlocked screen:** set Auto-Lock = Never, keep on power.
