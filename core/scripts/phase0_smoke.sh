#!/usr/bin/env bash
# Phase 0 smoke test — verify the sanctioned primitives on a real device.
# Run each block and confirm the pass/fail criteria in docs/PHASE0.md.
#
# Usage: bash phase0_smoke.sh <UDID>
set -uo pipefail
UDID="${1:?usage: phase0_smoke.sh <UDID>}"

echo "== 1. Device visible to CoreDevice =="
xcrun devicectl list devices || echo "FAIL: devicectl not available / no device"

echo "== 2. Screenshot (needs DDI mounted) =="
xcrun devicectl device screenshot --device "$UDID" /tmp/orch_shot.png \
  && echo "PASS: /tmp/orch_shot.png" || echo "FAIL: screenshot"

echo "== 3. Open URL (deep-link into an app) =="
xcrun devicectl device process openURL --device "$UDID" "https://www.apple.com" \
  && echo "PASS: openURL" || echo "FAIL: openURL"

echo "== 4. Confirm TikTok bundle id =="
xcrun devicectl device info apps --device "$UDID" 2>/dev/null | grep -i "zhiliao\|tiktok\|musically" \
  || echo "NOTE: confirm TikTok bundle id manually (expected com.zhiliaoapp.musically)"

echo "== 5. Tunnel (iOS 17+) — pick ONE backend =="
echo "   pymobiledevice3:  sudo pymobiledevice3 remote tunneld"
echo "   go-ios:           sudo ios tunnel start --userspace   (broken on iOS 26.5 #772)"

echo "== 6. Live-view options to benchmark =="
echo "   pymobiledevice3 core-device display serve-web --device $UDID"
echo "   (or AVFoundation USB capture in the native app; or WDA MJPEG :9100)"

echo "Done. See docs/PHASE0.md for pass/fail criteria and workarounds."
