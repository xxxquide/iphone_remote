#!/usr/bin/env bash
# Re-sign WebDriverAgent for a FREE Apple ID and reinstall on a device.
# Free profiles last 7 days — run this weekly (cron/launchd) or on-demand.
#
# Prereqs (one-time, done via Xcode GUI — see docs/SIGNING.md):
#   * WDA project built once with your (secondary) Apple ID / personal team
#   * Apple Development cert exported from Keychain as .p12
#   * device Trusted: Settings > General > VPN & Device Management > Trust
#
# Usage:  bash resign_wda.sh <UDID>
# Env:    P12_FILE, P12_PASSWORD, PROFILE_DIR, WDA_APP, BUNDLE_ID
set -euo pipefail

UDID="${1:?usage: resign_wda.sh <UDID>}"
P12_FILE="${P12_FILE:-$HOME/.orch/wda.p12}"
PROFILE_DIR="${PROFILE_DIR:-$HOME/Library/Developer/Xcode/UserData/Provisioning Profiles}"
WDA_APP="${WDA_APP:-$HOME/.orch/WebDriverAgentRunner-Runner.app}"
BUNDLE_ID="${BUNDLE_ID:-dev.orch.WebDriverAgentRunner}"   # must match your free profile

echo "[resign] device=$UDID bundle=$BUNDLE_ID"

# Option A: appium's bundled helper (recommended)
if command -v appium >/dev/null 2>&1; then
  P12_PASSWORD="${P12_PASSWORD:-}" appium driver run xcuitest sign-wda -- \
    --wda-path="$WDA_APP" \
    --p12-file="$P12_FILE" \
    --profile-dir="$PROFILE_DIR" \
    --bundle-id="$BUNDLE_ID"
else
  # Option B: appium/resigner directly
  P12_PASSWORD="${P12_PASSWORD:-}" resigner \
    --p12-file "$P12_FILE" \
    --profile "$PROFILE_DIR" \
    --force \
    --bundle-id-remap "com.facebook.WebDriverAgentRunner=$BUNDLE_ID" \
    --bundle-id-remap "com.facebook.WebDriverAgentRunner.xctrunner=$BUNDLE_ID.xctrunner" \
    "$WDA_APP"
fi

echo "[resign] reinstalling on device…"
xcrun devicectl device install app --device "$UDID" "$WDA_APP"

echo "[resign] done. NOTE: first launch needs the device online (signing validation)."
