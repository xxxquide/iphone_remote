#!/bin/bash
# ============================================================================
#  1-setup.command — double-click to install EVERYTHING the project needs.
#  Idempotent: safe to re-run any time. Fixes known landmines automatically:
#    * Node < 20.19  -> Appium 3 crashes (tracingChannel error). We install 22.
#    * go-ios is NOT in Homebrew core -> installed via npm.
#    * visionocr built INSIDE the repo (no sudo, no /usr/local writes).
#    * bare `pytest` can hit a conda python -> we always use `python -m pytest`.
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

echo "${BOLD}iphone-orchestrator · setup${RESET}  ${DIM}($REPO)${RESET}"

# ---------------------------------------------------------------- Xcode CLT --
step "Xcode command line tools"
if xcode-select -p >/dev/null 2>&1; then ok "installed: $(xcode-select -p)"
else warn "installing (a GUI dialog may appear — accept it, then re-run me)"; xcode-select --install || true; fi

# ----------------------------------------------------------------- Homebrew --
step "Homebrew"
if command -v brew >/dev/null 2>&1; then ok "$(brew --version | head -1)"
else
  warn "not found — installing"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || bad "brew install failed"
  for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$p" ] && eval "$($p shellenv)"; done
fi
export HOMEBREW_NO_AUTO_UPDATE=1   # keep this script fast & quiet

# ------------------------------------------------------------------- ffmpeg --
step "ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then ok "present"; else brew install ffmpeg && ok "installed" || bad "failed"; fi

# --------------------------------------------------------------------- Node --
# Appium 3 requires Node >= 20.19. Node 18 installs fine but CRASHES at runtime.
step "Node.js (>= 20.19 required by Appium 3)"
node_ok=false
if command -v node >/dev/null 2>&1; then
  NV="$(node --version)"; MAJ=${NV#v}; MAJ=${MAJ%%.*}; MIN=$(echo "${NV#v}" | cut -d. -f2)
  if [ "$MAJ" -gt 20 ] || { [ "$MAJ" -eq 20 ] && [ "$MIN" -ge 19 ]; }; then
    ok "$NV (supported)"; node_ok=true
  else
    warn "$NV is TOO OLD for Appium 3 — installing node@22 via brew"
  fi
else warn "not installed — installing node@22"; fi

if [ "$node_ok" = false ]; then
  brew install node@22 || brew install node || bad "node install failed"
  # node@22 is keg-only: expose it for this session AND future shells.
  for pfx in /opt/homebrew/opt/node@22 /usr/local/opt/node@22; do
    if [ -d "$pfx/bin" ]; then
      export PATH="$pfx/bin:$PATH"
      for rc in "$HOME/.zshrc" "$HOME/.bash_profile"; do
        [ -f "$rc" ] || continue
        grep -q "node@22/bin" "$rc" || echo "export PATH=\"$pfx/bin:\$PATH\"" >> "$rc"
      done
      ok "node@22 on PATH (added to shell rc): $("$pfx/bin/node" --version)"
    fi
  done
  command -v node >/dev/null && ok "node now: $(node --version)" || bad "node still missing"
fi

# ------------------------------------------------------------------- Appium --
step "Appium + XCUITest driver"
NV="$(node --version 2>/dev/null || echo v0)"; MAJ=${NV#v}; MAJ=${MAJ%%.*}
if [ "${MAJ:-0}" -lt 20 ]; then
  bad "Node is still $NV — open a NEW terminal (or re-run me) so node@22 is picked up, then continue"
else
  npm i -g appium >/dev/null 2>&1 && ok "appium installed" || warn "npm i -g appium reported issues"
  if appium --version >/dev/null 2>&1; then
    ok "appium runs: $(appium --version)"
    appium driver list --installed 2>/dev/null | grep -q xcuitest \
      && ok "xcuitest driver present" \
      || { appium driver install xcuitest >/dev/null 2>&1 && ok "xcuitest driver installed" || warn "driver install failed"; }
  else
    bad "appium installed but fails to run (see: appium --version)"
  fi
  # go-ios: NOT in Homebrew core — npm is the supported route.
  if command -v ios >/dev/null 2>&1; then ok "go-ios present"
  else npm i -g go-ios >/dev/null 2>&1 && ok "go-ios installed (npm)" || warn "go-ios optional — skipped"; fi
fi

# ---------------------------------------------------- Python venv + deps ----
step "Python venv + dependencies"
cd "$REPO/core"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements-dev.txt && ok "core deps installed"
python -m pip install -q -U pymobiledevice3 && ok "pymobiledevice3 installed"
cd "$REPO"

# ---------------------------------------------------------------- visionocr --
step "visionocr helper (Apple Vision OCR)"
if swift build --package-path tools/visionocr -c release >/dev/null 2>&1; then
  ok "built: tools/visionocr/.build/release/visionocr  (doctor finds it here — no sudo needed)"
else
  warn "swift build failed (needs Xcode); OCR level of the cascade will be skipped"
fi

# ------------------------------------------------------------------- config --
step "Local config (.env / devices.json)"
if [ ! -f .env ]; then
  cp .env.example .env
  TOKEN="$(python3 -c 'import secrets;print(secrets.token_hex(8))')"
  MEDIA="$(python3 -c 'import secrets;print(secrets.token_hex(12))')"
  # macOS sed needs the empty -i arg
  sed -i '' "s/^ORCH_TOKEN=.*/ORCH_TOKEN=$TOKEN/" .env
  sed -i '' "s/^ORCH_MEDIA_TOKEN=.*/ORCH_MEDIA_TOKEN=$MEDIA/" .env
  ok ".env created with random tokens (clears the doctor's media-token warning)"
else ok ".env already exists (left untouched)"; fi
[ -f devices.json ] || { cp devices.json.example devices.json; ok "devices.json created — put real UDIDs in it for REAL mode"; }

# -------------------------------------------------------------------- tests --
step "Test suite"
cd "$REPO/core"; source .venv/bin/activate
PYTHONPATH=. python -m pytest tests -q && ok "tests pass" || bad "tests failed (send me the output)"
cd "$REPO"

# ------------------------------------------------------------------- doctor --
step "Phase 0 doctor"
cd "$REPO/core"; source .venv/bin/activate
PYTHONPATH=. python -m core.phase0 || true
cd "$REPO"

echo
echo "${BOLD}Next:${RESET}"
echo "  ${BOLD}./2-run.command${RESET}     start the core + open the dashboard"
echo "  ${BOLD}./3-doctor.command${RESET}  re-check readiness any time"
echo "  ${BOLD}./4-real-mode.command${RESET} switch to real devices (guided)"
echo
echo "${DIM}If Node was just installed, open a NEW terminal window before running Appium.${RESET}"
echo "Press Return to close…"; read -r _
