#!/usr/bin/env bash
# Resume the autolab loop for the active project (AUTOLAB_PROJECT env var).
# Used by ./resume and by tools/idle_continue.py.
set -euo pipefail

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

exec uv run python tools/run_orchestrator.py --resume "$@" \
  >> "$LOG_DIR/orchestrator.log" 2>&1
