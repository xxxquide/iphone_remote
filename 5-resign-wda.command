#!/bin/bash
# ============================================================================
#  5-resign-wda.command — re-sign WebDriverAgent (free Apple ID = 7-day certs).
#  Run this when WDA stops launching ("Profile expired" / timeout message:5).
#  Uses the repo's signing helper for every device in devices.json.
# ============================================================================
set -uo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"

# Shared bootstrap: fixes PATH (keg-only node@22, npm globals, visionocr),
# provides step/ok/warn/bad helpers. Scripts run under bash and do NOT read
# ~/.zshrc, so without this Appium/node would look missing or too old.
# shellcheck disable=SC1091
source "$(dirname "$0")/orch-lib.sh"

ok()   { echo "  ${GREEN}✓${RESET} $*"; }

echo "${BOLD}iphone-orchestrator · re-sign WebDriverAgent${RESET}"

if [ ! -f devices.json ]; then
  warn "devices.json missing — run ./4-real-mode.command first"
  echo "Press Return to close…"; read -r _; exit 1
fi

echo
echo "${DIM}One-time prerequisites (see docs/SIGNING.md):"
echo "  ~/.orch/wda.p12  (Apple Development cert exported from Keychain)"
echo "  ~/.orch/WebDriverAgentRunner-Runner.app  (built once via Xcode)"
echo "  export P12_PASSWORD=... if your .p12 has a password${RESET}"
echo

UDIDS=$(python3 -c "import json;print(' '.join(d['udid'] for d in json.load(open('devices.json'))))")
for u in $UDIDS; do
  echo "${BOLD}--- $u ---${RESET}"
  bash core/scripts/resign_wda.sh "$u" && ok "re-signed $u" || warn "failed for $u (see output above)"
done

echo
echo "${DIM}Keep the phone online on first launch — iOS validates the signature.${RESET}"
echo "Then verify with ./3-doctor.command"
echo "Press Return to close…"; read -r _
