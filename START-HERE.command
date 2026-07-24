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

BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; BLUE=$'\033[34m'; RESET=$'\033[0m'

echo "${BOLD}iphone-orchestrator · START HERE${RESET}"

echo; echo "${BLUE}${BOLD}==> making every script double-clickable${RESET}"
chmod +x ./*.command 2>/dev/null
chmod +x core/scripts/*.sh 2>/dev/null
echo "  ${GREEN}✓${RESET} done — you can double-click any N-*.command from now on"

echo; echo "${BLUE}${BOLD}==> running full setup (this installs everything)${RESET}"
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
