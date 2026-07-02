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
# IDEA="We want to build an AI superforecaster. We want to predict arbitrary future events including one-off non-repeatable events like geopolitical events but also potentially more frequent phenomena like macro economic reporting data. We want to at once leverage patterns in numerical data and at the same time to engage in open world reasoning (for example: when forecasting demand for a product, evidence might come from numerical trends and month-over-month purchasing data but also in the form of online chatter or product reviews). Ideal system should be able to adaptively leverage the appropriate mode of inquiry depending on the query. Taken in aggregate across a large population of queries, predictions should be both internally consistent and probabilistically coherent."

IDEA="Models are uncreative — good at execution of boring problems bad at finding interesting problems to tackle and collapse to the mode of boring approaches. Is how we are training models today not conducive to this type of creative thinking? Can we marry a creative ideation model w/ a frontier execution model that presents the best of both worlds?"

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

# Cap run→design loopbacks. After `run`, if no experiment produced a
# positive result, the orchestrator loops back to `design` to try a
# different experimental setup (keeping the same hypotheses). After this
# many cycles, it falls through to `critique` where the broader
# experiment-retreat may park the hypotheses and retreat to `survey`.
export AUTOLAB_MAX_RUN_DESIGN_CYCLES="${AUTOLAB_MAX_RUN_DESIGN_CYCLES:-1000}"

# Cap committee-review loopbacks. After this many rounds, the paper ships
# unconditionally regardless of reviewer recommendations. Each cycle =
# 3 reviewers (methodologist, domain-expert, clarity-reviewer) running in
# parallel; any reviewer voting `major_revision` with a valid target_phase
# triggers a loopback to that phase.
export AUTOLAB_MAX_REVIEW_CYCLES="${AUTOLAB_MAX_REVIEW_CYCLES:-5}"

# ---------------------------------------------------------------------------
# 3. Optional kill-switches for the two paper-finishing steps.
# ---------------------------------------------------------------------------
# Uncomment either to skip that step. The orchestrator still runs every
# other phase normally; only the named step is bypassed.

# Skip the polish pass at the end of `final` (saves ~1 fable call). The
# unpolished assembled paper is still written to drafts/paper-vFINAL.md.
# export AUTOLAB_SKIP_POLISH=1

# Skip the committee-review phase entirely (saves 3 fable calls per cycle).
# The paper ships straight from `final` with no reviewer feedback.
# export AUTOLAB_SKIP_REVIEW=1

# ---------------------------------------------------------------------------
# 4. Optional CLI flags for scripts/start.
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
# 5. Build the argv to scripts/start and invoke.
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

echo ">>> AUTOLAB_MAX_IDEA_CYCLES      = $AUTOLAB_MAX_IDEA_CYCLES"
echo ">>> AUTOLAB_MAX_CYCLES           = $AUTOLAB_MAX_CYCLES"
echo ">>> AUTOLAB_MIN_WILD_HYPOTHESES  = $AUTOLAB_MIN_WILD_HYPOTHESES"
echo ">>> AUTOLAB_MAX_CRASH_RETRIES    = $AUTOLAB_MAX_CRASH_RETRIES"
echo ">>> AUTOLAB_MAX_RUN_DESIGN_CYCLES = $AUTOLAB_MAX_RUN_DESIGN_CYCLES"
echo ">>> AUTOLAB_MAX_REVIEW_CYCLES    = $AUTOLAB_MAX_REVIEW_CYCLES"
echo ">>> AUTOLAB_SKIP_POLISH         = ${AUTOLAB_SKIP_POLISH:-(unset)}"
echo ">>> AUTOLAB_SKIP_REVIEW         = ${AUTOLAB_SKIP_REVIEW:-(unset)}"
echo ">>> scripts/start ${ARGS[*]}"
echo

exec scripts/start "${ARGS[@]}"
