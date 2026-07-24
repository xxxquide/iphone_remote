# Signing WebDriverAgent without a paid Apple Developer account

All confirmed against Appium docs + appium/resigner + 2026 sideloading guides.

## The constraints (free Apple ID)
| Fact | Value |
|---|---|
| Profile validity | **7 days** |
| App ID slots | ~3 active; **WDA uses 2** (`.driver` + `.driver.xctrunner`) |
| App IDs / 7 days | 10 |
| Trust | manual, once per identity/device (Settings → VPN & Device Management) |
| Validation | device needs internet on first launch (iOS 16+) |

Because WDA eats 2 of ~3 slots, we **do not** build an on-device companion in v1.

## One-time setup
1. Xcode → Settings → Accounts → add your **secondary** Apple ID.
2. `appium driver run xcuitest open-wda` → enable *Automatically manage signing*,
   pick your personal team, choose a unique bundle id (e.g. `dev.orch.WebDriverAgentRunner`).
3. Build once on each real device (**Product ▸ Test**). Trust on the device.
4. Keychain Access → *My Certificates* → export **Apple Development** cert as
   `~/.orch/wda.p12` (set `P12_PASSWORD`).
5. Copy the built `WebDriverAgentRunner-Runner.app` to `~/.orch/`.

## Weekly re-sign (automated)
The core's Signing Manager detects when the profile is within
`ORCH_WDA_RESIGN_DAYS` of expiry and runs:
```bash
bash core/scripts/resign_wda.sh <UDID>
```
which calls `appium sign-wda` (or `resigner`) and reinstalls via `devicectl`.
Schedule it (launchd/cron) or let the core trigger it. Because the Mac is always
nearby, this "AltServer model" is more reliable than SideStore's on-device
refresh (which relies on a JIT/VPN helper that is broken on iOS 26.4–26.5).

## Tips
- Use a **secondary** Apple ID (not your main one).
- Keep the first launch online (signing validation).
- If you hit "maximum number of App IDs", wait for the 7-day quota or reuse ids.
