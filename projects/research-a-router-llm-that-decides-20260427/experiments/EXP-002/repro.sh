#!/usr/bin/env bash
# Reproduce EXP-002: Portfolio batch routing vs independent per-query routing
set -euo pipefail
cd "$(dirname "$0")/../.."
export AUTOLAB_PROJECT="research-a-router-llm-that-decides-20260427"

echo "=== Sanity gate ==="
python experiments/EXP-002/code/run.py --sanity --seeds 42,123,456

echo ""
echo "=== Full run ==="
python experiments/EXP-002/code/run.py --seeds 42,123,456
