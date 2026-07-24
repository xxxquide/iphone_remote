#!/bin/bash
# ============================================================================
#  START-HERE.command — the ONLY file you may need to fix by hand.
#
#  GitHub's API cannot set the executable bit, so freshly-pulled .command files
#  may not be double-clickable. This script fixes that for every script in the
#  repo, then runs setup + doctor for you.
#
#  If double-clicking THIS file does nothing, run once in Terminal:
#      chmod +x ~/Downloads/iphone_remote/*.command
#  …and from then on every script is double-clickable, forever.
# ============================================================================
set -uo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"

# Shared bootstrap: fixes PATH (keg-only node@22, npm globals, visionocr) and
# provides step/ok/warn/bad helpers. Scripts run under bash and do NOT read
# ~/.zshrc, so without this Appium/node would look missing or too old.
# shellcheck disable=SC1091
source "$REPO/orch-lib.sh"

echo "${BOLD}iphone-orchestrator · START HERE${RESET}"

step "making every script double-clickable"
chmod +x ./*.command 2>/dev/null
chmod +x ./orch-lib.sh 2>/dev/null
chmod +x core/scripts/*.sh 2>/dev/null
ok "done — you can double-click any N-*.command from now on"

step "running full setup (this installs everything)"
echo "${DIM}Takes a few minutes on first run. Follow any prompts.${RESET}"
./1-setup.command

echo
echo "${BOLD}All set.${RESET} From now on use:"
echo "  ${BOLD}2-run.command${RESET}       start + open dashboard"
echo "  ${BOLD}3-doctor.command${RESET}    readiness report"
echo "  ${BOLD}4-real-mode.command${RESET} switch to real iPhones"
echo "  ${BOLD}0-update.command${RESET}    pull my latest changes"
echo
echo "Press Return to close…"; read -r _
