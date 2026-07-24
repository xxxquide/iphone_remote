#!/bin/bash
# ============================================================================
#  2-run.command — double-click to start the core and open the dashboard.
#  Frees a stale port, starts the server, opens the browser UI automatically.
#  Ctrl-C in this window stops it.
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

if [ ! -d core/.venv ]; then
  echo "${YELLOW}No venv yet — run ./1-setup.command first.${RESET}"
  echo "Press Return to close…"; read -r _; exit 1
fi

# Read .env values the same way the app does: strip inline comments + spaces.
env_val() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- \
            | sed -e 's/[[:space:]]*#.*$//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'; }
PORT="$(env_val ORCH_PORT)"; PORT="${PORT:-8787}"
MODE="$(env_val ORCH_MOCK)"; MODE="${MODE:-true}"
[ "$MODE" = "false" ] && MODE_LABEL="REAL DEVICES" || MODE_LABEL="MOCK"

echo "${BOLD}iphone-orchestrator · run${RESET}   mode: ${BOLD}$MODE_LABEL${RESET}   port: $PORT"

# Free the port if a previous run is still holding it.
if lsof -ti tcp:"$PORT" >/dev/null 2>&1; then
  warn "port $PORT busy — stopping the old instance"
  lsof -ti tcp:"$PORT" | xargs kill -9 2>/dev/null || true
  sleep 1
fi

cd core
# shellcheck disable=SC1091
source .venv/bin/activate

# Open the dashboard once the server answers.
( for _ in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
      open "http://127.0.0.1:$PORT/"; break
    fi
    sleep 0.5
  done ) &

ok "starting core — the dashboard opens by itself"
echo "${DIM}Press Ctrl-C to stop.${RESET}"
echo
PYTHONPATH=. python -m core

echo
echo "Core stopped. Press Return to close…"; read -r _
