#!/bin/bash
# ============================================================================
#  3-doctor.command — double-click for a full readiness report.
#  Runs the test suite + Phase 0 doctor. Tools are VERIFIED BY RUNNING them,
#  so "installed but broken" (e.g. Appium on old Node) shows up as FAIL.
# ============================================================================
set -uo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"

BOLD=$'\033[1m'; DIM=$'\033[2m'; BLUE=$'\033[34m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'

if [ ! -d core/.venv ]; then
  echo "${YELLOW}No venv yet — run ./1-setup.command first.${RESET}"
  echo "Press Return to close…"; read -r _; exit 1
fi

echo "${BOLD}iphone-orchestrator · doctor${RESET}"
echo "${DIM}repo: $REPO${RESET}"

# Surface useful environment facts the doctor can't know about.
echo; echo "${BLUE}${BOLD}==> environment${RESET}"
echo "  macOS      : $(sw_vers -productVersion 2>/dev/null || echo '?')"
echo "  Xcode      : $(xcodebuild -version 2>/dev/null | head -1 || echo 'not found')"
echo "  node       : $(command -v node >/dev/null && node --version || echo 'missing')"
echo "  python     : $(core/.venv/bin/python --version 2>&1)"
echo "  connected  : $(xcrun devicectl list devices 2>/dev/null | grep -ci 'iphone' || echo 0) iPhone(s) seen by devicectl"

echo; echo "${BLUE}${BOLD}==> tests${RESET}"
cd core
# shellcheck disable=SC1091
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests -q || true

echo; echo "${BLUE}${BOLD}==> Phase 0 doctor${RESET}"
PYTHONPATH=. python -m core.phase0 || true
cd "$REPO"

echo
echo "${DIM}FAIL = must fix · WARN = optional/nice-to-have · SKIP = can't check remotely${RESET}"
echo "Press Return to close…"; read -r _
