#!/usr/bin/env bash
# Reproduces EXP-004: Contextual Thompson Sampling Router vs Static Baseline
# Seeds: 42, 123, 7, 2024, 99
set -euo pipefail

cd "$(dirname "$0")"

echo "[repro] Running sanity gate..."
uv run --with scikit-learn --with numpy python code/run.py --sanity --seed 42

echo "[repro] Running full 5-seed sweep..."
uv run --with scikit-learn --with numpy python code/run.py --out result.json

echo "[repro] Done. Results in result.json"
