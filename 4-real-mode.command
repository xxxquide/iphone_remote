#!/bin/bash
# ============================================================================
#  4-real-mode.command — guided switch from MOCK to REAL devices.
#  Detects your connected iPhones, writes their real UDIDs into devices.json,
#  mounts the developer disk image, and flips ORCH_MOCK=false.
#  Everything it cannot do for you (Developer Mode, Trust, signing WDA) is
#  printed as an explicit checklist.
# ============================================================================
set -uo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"

BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'
RED=$'\033[31m'; BLUE=$'\033[34m'; RESET=$'\033[0m'
step() { echo; echo "${BLUE}${BOLD}==> $*${RESET}"; }
ok()   { echo "  ${GREEN}✓${RESET} $*"; }
warn() { echo "  ${YELLOW}!${RESET} $*"; }
bad()  { echo "  ${RED}✗${RESET} $*"; }

echo "${BOLD}iphone-orchestrator · switch to REAL devices${RESET}"

step "Prerequisites you must do ON EACH iPhONE (once)"
cat <<'TXT'
  1. Settings > Privacy & Security > Developer Mode  ->  ON  (device reboots)
  2. Connect by USB, tap "Trust This Computer", enter passcode
  3. Settings > Display & Brightness > Auto-Lock  ->  Never   (keep screen awake)
  4. Keep the phone unlocked while automation runs
TXT
echo "  Press Return when both phones are connected & trusted…"; read -r _

step "Detecting connected devices (devicectl)"
TMP="$(mktemp -t orchdev).json"
if ! xcrun devicectl list devices --json-output "$TMP" >/dev/null 2>&1; then
  bad "devicectl failed — is Xcode installed? (xcode-select -p)"
  echo "Press Return to close…"; read -r _; exit 1
fi

cd core
# shellcheck disable=SC1091
source .venv/bin/activate
cd "$REPO"

python3 - "$TMP" <<'PY'
import json, sys, pathlib
raw = json.load(open(sys.argv[1]))
devs = []
for d in raw.get("result", {}).get("devices", []):
    hw, props = d.get("hardwareProperties", {}), d.get("deviceProperties", {})
    if "iPhone" not in str(hw.get("deviceType", "")) + str(props.get("name", "")):
        continue
    devs.append({"udid": hw.get("udid", ""), "name": props.get("name", "iPhone"),
                 "ios": str(props.get("osVersionNumber", ""))})
if not devs:
    print("  \033[31m✗\033[0m no iPhones found — check USB / Trust / Developer Mode")
    sys.exit(2)

# Screen geometry per model (logical points) so taps map correctly.
GEO = {"iPhone 15 Pro Max": (430, 932), "iPhone XS Max": (414, 896)}
out = []
for i, d in enumerate(devs):
    w, h = GEO.get(d["name"], (390, 844))
    out.append({
        "udid": d["udid"], "name": d["name"], "ios": d["ios"],
        "wda_port": 8100 + i, "mjpeg_port": 9100 + i,
        "tiktok_bundle_id": "com.zhiliaoapp.musically",
        "vpn_expected_region": "", "scale": 3.0, "point_w": w, "point_h": h,
    })
    print(f"  \033[32m✓\033[0m {d['name']}  iOS {d['ios']}  {d['udid']}  ({w}x{h} pt)")
    if d["ios"].startswith(("26.4", "26.5")):
        print("     \033[33m!\033[0m iOS 26.4/26.5: go-ios userspace tunnel is broken (#772)"
              " -> use pymobiledevice3 tunneld")
pathlib.Path("devices.json").write_text(json.dumps(out, indent=2) + "\n")
print(f"  \033[32m✓\033[0m devices.json written ({len(out)} device(s))")
PY
rc=$?
rm -f "$TMP"
[ $rc -ne 0 ] && { echo; echo "Press Return to close…"; read -r _; exit $rc; }

step "Mounting developer disk image (needed for screenshots/automation)"
cd core; source .venv/bin/activate; cd "$REPO"
python -m pymobiledevice3 mounter auto-mount 2>/dev/null && ok "DDI mounted" \
  || warn "auto-mount reported an issue (often already mounted — fine)"

step "Flipping .env to REAL mode"
[ -f .env ] || cp .env.example .env
if grep -q '^ORCH_MOCK=' .env; then sed -i '' 's/^ORCH_MOCK=.*/ORCH_MOCK=false/' .env
else echo 'ORCH_MOCK=false' >> .env; fi
ok "ORCH_MOCK=false"

step "Remaining manual step: sign WebDriverAgent (free Apple ID, once per 7 days)"
cat <<'TXT'
  appium driver run xcuitest open-wda        # opens the WDA project in Xcode
  In Xcode:  Signing & Capabilities -> Automatically manage signing
             -> pick your (secondary) Apple ID team
             -> select the device -> Product ▸ Test
  On the phone: Settings > General > VPN & Device Management > Trust
  (Free profiles expire after 7 days — ./5-resign-wda.command re-does it.)
TXT

step "Verifying"
cd core; source .venv/bin/activate
PYTHONPATH=. python -m core.phase0 || true
cd "$REPO"

echo
echo "${BOLD}Then:${RESET} ./2-run.command   ${DIM}(now drives the real phones)${RESET}"
echo "Press Return to close…"; read -r _
