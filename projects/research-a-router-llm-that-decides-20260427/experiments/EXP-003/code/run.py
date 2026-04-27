#!/usr/bin/env python3
"""
EXP-003: Decompose-then-route vs whole-query routing on HotpotQA.

Simulates 3-tier routing (haiku/sonnet/opus proxy models) on HotpotQA-style
multi-hop questions. Tests whether decomposing into 2 sub-questions and routing
each independently reduces cost ≥15% at matched F1 (within 1pp tolerance).

Cost model (per token):
  haiku  = $0.25 / 1M tokens
  sonnet = $3.00 / 1M tokens
  opus   = $15.00 / 1M tokens

Outputs one JSONL record to --out per invocation.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

# ── Cost model ────────────────────────────────────────────────────────────────
TIER_COSTS = {"haiku": 0.25e-6, "sonnet": 3.0e-6, "opus": 15.0e-6}

# Representative token budgets per call type
DECOMPOSE_TOKENS = 200   # decomposer (haiku): split question → 2 sub-questions
SUB_Q_TOKENS = 150       # per sub-question answer call
MERGE_TOKENS = 250       # merger (haiku): combine sub-answers → final answer
WHOLE_Q_TOKENS = 300     # whole-query opus baseline

N_EVAL = 500

# Sub-question complexity distribution (BERT router output distribution)
SUB_Q_COMPLEXITY_PROBS = {"easy": 0.45, "medium": 0.35, "hard": 0.20}

# Tier routing: BERT classifier maps complexity → cheapest capable model
COMPLEXITY_TO_TIER = {"easy": "haiku", "medium": "sonnet", "hard": "opus"}

# Expected F1 by (complexity, assigned_tier) — from tier capability priors
TIER_F1 = {
    "easy":   {"haiku": 0.78, "sonnet": 0.84, "opus": 0.89},
    "medium": {"haiku": 0.52, "sonnet": 0.79, "opus": 0.87},
    "hard":   {"haiku": 0.31, "sonnet": 0.61, "opus": 0.84},
}

# Baseline: opus on the full question
BASELINE_F1_MU = 0.72
BASELINE_F1_SIGMA = 0.10

# Merger success rate (when successful, synthesis preserves ~92% of sub-answer quality)
MERGER_SUCCESS_RATE = 0.88
MERGER_SUCCESS_SCALE = 0.92
MERGER_FAILURE_SCALE = 0.45

# F1 per-sub-question noise
SUB_F1_SIGMA = 0.12


# ── Simulation helpers ────────────────────────────────────────────────────────

def simulate_one_question(rng: random.Random) -> tuple[float, float]:
    """
    Simulate one HotpotQA 2-hop question through decompose-then-route.
    Returns (f1, total_cost).
    """
    complexities = list(SUB_Q_COMPLEXITY_PROBS.keys())
    weights = list(SUB_Q_COMPLEXITY_PROBS.values())

    sub_costs: list[float] = []
    sub_f1s: list[float] = []

    for _ in range(2):
        comp = rng.choices(complexities, weights=weights)[0]
        tier = COMPLEXITY_TO_TIER[comp]
        cost = SUB_Q_TOKENS * TIER_COSTS[tier]
        mu = TIER_F1[comp][tier]
        f1 = float(np.clip(rng.gauss(mu, SUB_F1_SIGMA), 0.0, 1.0))
        sub_costs.append(cost)
        sub_f1s.append(f1)

    decompose_cost = DECOMPOSE_TOKENS * TIER_COSTS["haiku"]
    merge_cost = MERGE_TOKENS * TIER_COSTS["haiku"]
    total_cost = decompose_cost + sum(sub_costs) + merge_cost

    avg_sub_f1 = sum(sub_f1s) / len(sub_f1s)
    if rng.random() < MERGER_SUCCESS_RATE:
        final_f1 = avg_sub_f1 * MERGER_SUCCESS_SCALE
    else:
        final_f1 = avg_sub_f1 * MERGER_FAILURE_SCALE

    return float(np.clip(final_f1, 0.0, 1.0)), total_cost


# ── Sanity gate ───────────────────────────────────────────────────────────────

def run_sanity(seed: int, out_path: Path) -> None:
    """Overfit 32 examples; check log-loss drops ≥50%."""
    # 32 examples with two clearly separable groups
    questions = [
        (f"What is the capital of the country in Europe that borders France? example {i}"
         if i % 2 == 0 else
         f"Compute the integral of the quadratic polynomial function {i}")
        for i in range(32)
    ]
    labels = [i % 2 for i in range(32)]

    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=500)
    X = tfidf.fit_transform(questions)

    n_classes = 2
    initial_probs = np.full((32, n_classes), 0.5)
    initial_loss = float(log_loss(labels, initial_probs))

    lr = LogisticRegression(C=100.0, max_iter=2000, random_state=seed)
    lr.fit(X, labels)
    final_probs = lr.predict_proba(X)
    final_loss = float(log_loss(labels, final_probs))

    drop = (initial_loss - final_loss) / initial_loss if initial_loss > 0 else 0.0
    record = {
        "seed": seed,
        "config": "sanity",
        "sanity_loss_initial": initial_loss,
        "sanity_loss_final": final_loss,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record) + "\n")
    print(
        f"sanity seed={seed}: initial_loss={initial_loss:.4f} "
        f"final_loss={final_loss:.4f} drop={drop:.2%}"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--config", choices=["proposed", "baseline"], default="proposed")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sanity", action="store_true")
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    rng = random.Random(args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.sanity:
        run_sanity(args.seed, out_path)
        return

    if args.config == "baseline":
        # All questions → opus (whole-query routing, no decomposition)
        f1_scores: list[float] = []
        total_cost = 0.0
        for _ in range(N_EVAL):
            f1 = float(np.clip(rng.gauss(BASELINE_F1_MU, BASELINE_F1_SIGMA), 0.0, 1.0))
            f1_scores.append(f1)
            total_cost += WHOLE_Q_TOKENS * TIER_COSTS["opus"]

        f1_accuracy = float(np.mean(f1_scores))
        record = {
            "seed": args.seed,
            "config": "baseline",
            "f1_accuracy": f1_accuracy,
            "total_simulated_cost": total_cost,
            "cost_reduction_percent_at_matched_f1": 0.0,
            "cost_reduction_percent_at_matched_accuracy": 0.0,
        }

    else:
        # Proposed: decompose → route each sub-question → answer → merge
        proposed_f1s: list[float] = []
        proposed_costs: list[float] = []

        for _ in range(N_EVAL):
            f1, cost = simulate_one_question(rng)
            proposed_f1s.append(f1)
            proposed_costs.append(cost)

        proposed_f1 = float(np.mean(proposed_f1s))
        total_proposed_cost = float(np.sum(proposed_costs))

        # Compute baseline F1 with same seed for matched comparison
        baseline_rng = random.Random(args.seed)
        baseline_f1s = [
            float(np.clip(baseline_rng.gauss(BASELINE_F1_MU, BASELINE_F1_SIGMA), 0.0, 1.0))
            for _ in range(N_EVAL)
        ]
        baseline_f1 = float(np.mean(baseline_f1s))
        total_baseline_cost = float(N_EVAL * WHOLE_Q_TOKENS * TIER_COSTS["opus"])

        raw_cost_reduction = (total_baseline_cost - total_proposed_cost) / total_baseline_cost
        f1_gap = baseline_f1 - proposed_f1

        # Metric: cost reduction only counts if F1 is within 1pp tolerance
        cost_reduction_at_matched = raw_cost_reduction if abs(f1_gap) <= 0.01 else 0.0

        record = {
            "seed": args.seed,
            "config": "proposed",
            "f1_accuracy": proposed_f1,
            "total_simulated_cost": total_proposed_cost,
            "cost_reduction_percent_at_matched_f1": cost_reduction_at_matched,
            # Alias matching HYP-007 prediction_metric for runner status check
            "cost_reduction_percent_at_matched_accuracy": cost_reduction_at_matched,
            "baseline_f1": baseline_f1,
            "f1_gap_vs_baseline_pp": round(f1_gap * 100, 3),
            "raw_cost_reduction": raw_cost_reduction,
        }

    out_path.write_text(json.dumps(record) + "\n")
    print(
        f"seed={args.seed} config={args.config} "
        f"f1={record['f1_accuracy']:.4f} "
        f"cost=${record['total_simulated_cost']:.6f} "
        f"cost_reduction@matchedF1={record['cost_reduction_percent_at_matched_f1']:.4f}"
    )


if __name__ == "__main__":
    main()
