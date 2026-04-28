#!/usr/bin/env bash
# example.sh — a worked example of running autolab end-to-end.
#
# This file is meant to be COPIED, not run as-is. It shows every knob the
# orchestrator exposes via CLI args and env vars. Comment out the bits you
# don't need before running.
#
# Run from the repo root:
#     bash example.sh
# or make it executable once and invoke directly:
#     chmod +x example.sh && ./example.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# ---------------------------------------------------------------------------
# 1. Seed idea (required). Pick exactly ONE of the three forms below.
# ---------------------------------------------------------------------------

# (a) Inline string. Safe for short ideas; avoid embedded apostrophes/quotes
#     because the shell will split them across argv.
IDEA="Come up with an improved version of DPO (direct preference optimization) that has never been implemented before but is motivated by current challenges with it."

# (b) From a file. Recommended for long, multi-paragraph ideas.
# IDEA_FILE="$REPO_DIR/my-idea.txt"

# (c) From stdin. Useful when piping from another tool. (Mutually exclusive
#     with the example.sh invocation pattern below; if you want stdin,
#     invoke scripts/start directly: `cat idea.txt | scripts/start --idea-stdin`.)

# ---------------------------------------------------------------------------
# 2. Tunable env vars (all optional — defaults shown).
# ---------------------------------------------------------------------------
# Cap idea-retreats (re-runs of expand) before giving up on the seed idea.
# Set to 0 to disable retreating.
export AUTOLAB_MAX_IDEA_CYCLES="${AUTOLAB_MAX_IDEA_CYCLES:-10}"

# Cap experiment-retreats (re-runs of survey..critique) before falling back
# to a negative-result paper.
export AUTOLAB_MAX_CYCLES="${AUTOLAB_MAX_CYCLES:-20}"

# Minimum number of hypotheses that must survive `screen` (boredom +
# novelty) for the run to proceed to `design`. Low values => fewer
# retreats; high values => stricter wildness bar.
export AUTOLAB_MIN_WILD_HYPOTHESES="${AUTOLAB_MIN_WILD_HYPOTHESES:-2}"

# Orchestrator-level crash retries per ExperimentPlan, on top of the
# in-skill 2 retries. Total worst-case attempts = 1 + 2 + this value.
export AUTOLAB_MAX_CRASH_RETRIES="${AUTOLAB_MAX_CRASH_RETRIES:-20}"

# ---------------------------------------------------------------------------
# 3. Optional CLI flags for scripts/start.
# ---------------------------------------------------------------------------
# Override the auto-generated project id (default: <slug>-<YYYYMMDD>).
# Useful when you want a stable, predictable directory name.
PROJECT_ID=""                 # e.g. "grpo-improvements-2026-04-27"

# Bias the experiment-designer toward a tracked benchmark (e.g. "mnist",
# "gsm8k"). Empty string disables the hint.
BENCHMARK=""                  # e.g. "gsm8k"

# Hands-off mode: run under the CPU-idle watchdog so the orchestrator
# auto-resumes on machine idle (handy for overnight runs).
WATCHDOG=0                    # 1 to enable

# Single-step mode: only run the seed phase, then exit. Useful for
# verifying setup without spending the full token budget.
SINGLE_STEP=0                 # 1 to enable

# ---------------------------------------------------------------------------
# 4. Build the argv to scripts/start and invoke.
# ---------------------------------------------------------------------------
ARGS=()

if [[ -n "${IDEA_FILE:-}" ]]; then
  ARGS+=(--idea-file "$IDEA_FILE")
elif [[ -n "${IDEA:-}" ]]; then
  ARGS+=(--idea "$IDEA")
else
  echo "ERROR: set IDEA or IDEA_FILE before running example.sh" >&2
  exit 2
fi

[[ -n "$PROJECT_ID" ]] && ARGS+=(--project-id "$PROJECT_ID")
[[ -n "$BENCHMARK"  ]] && ARGS+=(--benchmark "$BENCHMARK")
(( WATCHDOG ))         && ARGS+=(--watchdog)
(( SINGLE_STEP ))      && ARGS+=(--single-step)

echo ">>> AUTOLAB_MAX_IDEA_CYCLES     = $AUTOLAB_MAX_IDEA_CYCLES"
echo ">>> AUTOLAB_MAX_CYCLES          = $AUTOLAB_MAX_CYCLES"
echo ">>> AUTOLAB_MIN_WILD_HYPOTHESES = $AUTOLAB_MIN_WILD_HYPOTHESES"
echo ">>> AUTOLAB_MAX_CRASH_RETRIES   = $AUTOLAB_MAX_CRASH_RETRIES"
echo ">>> scripts/start ${ARGS[*]}"
echo

exec scripts/start "${ARGS[@]}"
