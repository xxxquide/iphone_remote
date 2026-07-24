#!/bin/bash
# ============================================================================
#  0-update.command — pull my latest changes, refresh deps, re-verify.
#  Run me first whenever I say "I pushed something". Keeps your local edits
#  safe by stashing them instead of clobbering.
# ============================================================================
set -uo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"

# --- self-protection -------------------------------------------------------
# `git pull` can REWRITE this very file while bash is still reading it (bash
# reads scripts lazily, by byte offset), which would make it execute garbage
# from the middle of the new file. So we re-exec from a temporary copy first
# and do all git work from there. No `git pull` needed before running me.
if [ "${ORCH_UPDATE_DETACHED:-0}" != "1" ]; then
  # `mktemp -t NAME` is macOS-style; the XXXXXX form works on macOS AND Linux.
  SELF_COPY="$(mktemp "${TMPDIR:-/tmp}/orch-update.XXXXXX")"
  cp "$0" "$SELF_COPY"
  chmod +x "$SELF_COPY"
  ORCH_UPDATE_DETACHED=1 ORCH_REPO="$REPO" exec /bin/bash "$SELF_COPY"
fi
# Running from the temp copy now: work on the real repo.
REPO="${ORCH_REPO:-$REPO}"
cd "$REPO"
trap 'rm -f "$0"' EXIT           # clean the temp copy on the way out

# Shared bootstrap: fixes PATH (keg-only node@22, npm globals, visionocr),
# provides step/ok/warn/bad helpers. Scripts run under bash and do NOT read
# ~/.zshrc, so without this Appium/node would look missing or too old.
# shellcheck disable=SC1091
source "$REPO/orch-lib.sh"

echo "${BOLD}iphone-orchestrator · update${RESET}"

# GitHub's API commits files as 100644, and our chmod +x then shows up as a
# "modification" (644->755), which BLOCKS every future pull. Telling git to
# ignore the exec bit in this repo makes the tree clean permanently.
if [ "$(git config --get core.fileMode 2>/dev/null)" != "false" ]; then
  git config core.fileMode false
  ok "git core.fileMode=false (exec-bit churn no longer blocks pulls)"
fi
# Drop any pre-existing mode-only diffs recorded before that setting.
git diff --name-only --diff-filter=M 2>/dev/null | while read -r f; do
  [ -n "$f" ] || continue
  if [ -z "$(git diff --numstat -- "$f" | awk '{print $1+$2}' | grep -v '^0$')" ]; then
    git checkout -- "$f" 2>/dev/null || true
  fi
done

step "Pulling latest"
BEFORE="$(git rev-parse --short HEAD 2>/dev/null || echo none)"
# Only TRACKED modifications can block a fast-forward. Untracked local files
# (.env, devices.json, data/) are yours — never stash those.
TRACKED_DIRTY="$(git status --porcelain --untracked-files=no 2>/dev/null)"
if [ -n "$TRACKED_DIRTY" ]; then
  warn "you modified tracked files — stashing them (restore later: git stash pop)"
  echo "$TRACKED_DIRTY" | sed 's/^/      /'
  git stash push -m "auto-stash by 0-update.command" >/dev/null 2>&1 || true
fi
git pull --ff-only || warn "pull failed (check your network / branch)"
AFTER="$(git rev-parse --short HEAD 2>/dev/null || echo none)"
[ "$BEFORE" = "$AFTER" ] && ok "already up to date ($AFTER)" || ok "updated: $BEFORE -> $AFTER"

step "Making scripts executable"
chmod +x ./*.command ./orch-lib.sh core/scripts/*.sh 2>/dev/null && ok "done"

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
