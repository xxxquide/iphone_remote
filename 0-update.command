#!/bin/bash
# ============================================================================
#  0-update.command — pull my latest changes, refresh deps, re-verify.
#  Run me first whenever I say "I pushed something". Keeps your local edits
#  safe by stashing them instead of clobbering.
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

echo "${BOLD}iphone-orchestrator · update${RESET}"

step "Pulling latest"
BEFORE="$(git rev-parse --short HEAD 2>/dev/null || echo none)"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  warn "you have local changes — stashing them (restore later: git stash pop)"
  git stash push -u -m "auto-stash by 0-update.command" >/dev/null 2>&1 || true
fi
git pull --ff-only || warn "pull failed (check your network / branch)"
AFTER="$(git rev-parse --short HEAD 2>/dev/null || echo none)"
[ "$BEFORE" = "$AFTER" ] && ok "already up to date ($AFTER)" || ok "updated: $BEFORE -> $AFTER"

step "Making .command files executable"
chmod +x ./*.command 2>/dev/null && ok "done"

step "Refreshing Python deps"
if [ -d core/.venv ]; then
  cd core
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install -q -r requirements-dev.txt && ok "deps up to date"
  cd "$REPO"
else
  warn "no venv — run ./1-setup.command"
fi

step "Rebuilding visionocr (if Xcode present)"
swift build --package-path tools/visionocr -c release >/dev/null 2>&1 \
  && ok "visionocr rebuilt" || warn "skipped"

step "Tests + doctor"
if [ -d core/.venv ]; then
  cd core; source .venv/bin/activate
  PYTHONPATH=. python -m pytest tests -q || true
  echo
  PYTHONPATH=. python -m core.phase0 || true
  cd "$REPO"
fi

echo
echo "${DIM}Next: ./2-run.command (start) · ./3-doctor.command (check) · ./4-real-mode.command (go real)${RESET}"
echo "Press Return to close…"; read -r _
