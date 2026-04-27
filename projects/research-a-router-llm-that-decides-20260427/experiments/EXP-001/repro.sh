#!/usr/bin/env bash
# Reproduce EXP-001: speculative cascade vs input-feature routing on GSM8K
set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$PROJ_ROOT/experiments/EXP-001/code/run.py"
RUNS="$PROJ_ROOT/experiments/EXP-001/runs"
mkdir -p "$RUNS"

# Sanity gate
python "$SCRIPT" --seed 42 --config proposed --out "$RUNS/sanity.json" --sanity

# Multi-seed sweep
for seed in 42 123 456; do
  for config in proposed baseline; do
    python "$SCRIPT" --seed "$seed" --config "$config" --out "$RUNS/seed${seed}_${config}.json"
  done
done

echo "All runs complete. Results in $RUNS/"
