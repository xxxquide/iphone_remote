#!/bin/bash
# ============================================================================
#  orch-lib.sh — shared bootstrap sourced by every *.command script.
#
#  WHY THIS EXISTS: the .command scripts run under `#!/bin/bash`, which does NOT
#  read ~/.zshrc. So a keg-only Homebrew node@22 that setup added to the zsh rc
#  is invisible here, and Appium (which needs Node >= 20.19) fails inside the
#  scripts even though it works in your interactive shell. We fix PATH in-process
#  so every script — and the Phase 0 doctor it runs — sees the same tools.
# ============================================================================

# Colors / helpers (shared by all scripts)
BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'
RED=$'\033[31m'; BLUE=$'\033[34m'; RESET=$'\033[0m'
step() { echo; echo "${BLUE}${BOLD}==> $*${RESET}"; }
ok()   { echo "  ${GREEN}✓${RESET} $*"; }
warn() { echo "  ${YELLOW}!${RESET} $*"; }
bad()  { echo "  ${RED}✗${RESET} $*"; }

orch_path_bootstrap() {
  # Homebrew itself (Apple silicon first, then Intel)
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -x "$b" ] && eval "$("$b" shellenv)" && break
  done
  # Modern Node BEFORE anything else: keg-only formulas are not symlinked.
  for pfx in /opt/homebrew/opt/node@24 /opt/homebrew/opt/node@22 \
             /usr/local/opt/node@24 /usr/local/opt/node@22; do
    [ -d "$pfx/bin" ] && PATH="$pfx/bin:$PATH"
  done
  # npm global bin (appium, go-ios) — respects a custom prefix like ~/.npm-global
  if command -v npm >/dev/null 2>&1; then
    npm_bin="$(npm bin -g 2>/dev/null || true)"
    [ -n "${npm_bin:-}" ] && [ -d "$npm_bin" ] && PATH="$npm_bin:$PATH"
    npm_pfx="$(npm config get prefix 2>/dev/null || true)"
    [ -n "${npm_pfx:-}" ] && [ -d "$npm_pfx/bin" ] && PATH="$npm_pfx/bin:$PATH"
  fi
  # This repo's locally built helpers (visionocr)
  [ -d "$PWD/tools/visionocr/.build/release" ] && PATH="$PWD/tools/visionocr/.build/release:$PATH"
  export PATH
}

# Activate the project's Python venv (no-op if missing).
orch_activate_venv() {
  if [ -f "$PWD/core/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$PWD/core/.venv/bin/activate"
    return 0
  fi
  return 1
}

# Report the node situation the way Appium cares about.
orch_node_status() {
  if ! command -v node >/dev/null 2>&1; then echo "missing"; return; fi
  local nv maj min
  nv="$(node --version)"; maj="${nv#v}"; maj="${maj%%.*}"
  min="$(echo "${nv#v}" | cut -d. -f2)"
  if [ "$maj" -gt 20 ] 2>/dev/null || { [ "$maj" -eq 20 ] && [ "$min" -ge 19 ]; } 2>/dev/null; then
    echo "ok $nv"
  else
    echo "old $nv"
  fi
}

orch_path_bootstrap
