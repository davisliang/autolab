#!/usr/bin/env bash
# Resume the autolab loop for the active project (AUTOLAB_PROJECT env var).
# Used by scripts/resume and by autolab.idle_continue.
set -euo pipefail

# This script lives at <repo>/scripts/continue_loop.sh, so REPO_DIR is one parent up.
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if [[ -z "${AUTOLAB_PROJECT:-}" ]]; then
  echo "continue_loop.sh: AUTOLAB_PROJECT must be set" >&2
  exit 2
fi

LOG_DIR="$REPO_DIR/projects/$AUTOLAB_PROJECT/logs"
mkdir -p "$LOG_DIR"

if [[ -f "$REPO_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_DIR/.env"
  set +a
fi

exec uv run python -m autolab.orchestrator --resume "$@" \
  >> "$LOG_DIR/orchestrator.log" 2>&1
