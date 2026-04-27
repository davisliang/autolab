#!/usr/bin/env python3
"""EXP-003: Portfolio Batch Knapsack Routing vs Independent Threshold Routing.

Tests HYP-008: batch-level budget-aware routing reduces API cost >=20% vs
independent per-query threshold routing at matched aggregate quality
(within 2pp of always-Opus).

3-tier setting: Haiku (cost 1), Sonnet (cost 5), Opus (cost 25).
1000 queries x 5 batches x 3 seeds on simulated RouterBench MMLU.

Both strategies see the SAME noisy difficulty estimates (sigma=0.12).
The only variable is whether allocation is global (knapsack) or local (threshold).

Usage:
  python run.py --seed 42 --config sanity --out results.jsonl
  python run.py --seed 42 --config full   --out results.jsonl
"""

import argparse
import json
import time

import numpy as np


# ---------------------------------------------------------------------------
# Constants — derived to match stated accuracy profile over Beta(2,3)
# Centers chosen so that E[sigmoid(-(d-c)/SLOPE)] over Beta(2,3) ~= target acc
# ---------------------------------------------------------------------------
N_QUERIES = 1000
N_BATCHES = 5

COSTS = np.array([1.0, 5.0, 25.0])       # Haiku, Sonnet, Opus
CENTERS = np.array([0.35, 0.55, 0.70])   # sigmoid midpoints; ~40%, ~73%, ~92% avg acc
SLOPE = 0.08
NOISE_STD = 0.12
QUALITY_TOL = 2.0 / 100.0   # within 2pp of always-Opus aggregate accuracy


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30.0, 30.0)))


def p_correct_matrix(d):
    """Return (N, 3) matrix: P(correct | difficulty d, tier t)."""
    return sigmoid(-(d[:, None] - CENTERS[None, :]) / SLOPE)


# ---------------------------------------------------------------------------
# Sanity gate
# ---------------------------------------------------------------------------
def spearman_corr(x, y):
    """Spearman rank correlation (no scipy required)."""
    n = len(x)
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    dx = rx - rx.mean()
    dy = ry - ry.mean()
    denom = np.sqrt((dx ** 2).sum() * (dy ** 2).sum())
    return float((dx * dy).sum() / denom) if denom > 0 else 0.0


def run_sanity(rng):
    """Sanity gate: Spearman(true_delta_HS, pred_delta_HS) on 32 examples > 0.5."""
    n = 32
    d = rng.beta(2, 3, size=n)
    noise = rng.normal(0, NOISE_STD, size=n)
    pred_d = np.clip(d + noise, 0, 1)

    true_pc = p_correct_matrix(d)
    pred_pc = p_correct_matrix(pred_d)

    true_delta = true_pc[:, 1] - true_pc[:, 0]   # H->S gain (true)
    pred_delta = pred_pc[:, 1] - pred_pc[:, 0]   # H->S gain (predicted)

    corr = spearman_corr(true_delta, pred_delta)
    return {
        "spearman_corr": round(corr, 4),
        "sanity_pass": bool(corr > 0.5),
        "n_examples": n,
    }


# ---------------------------------------------------------------------------
# Greedy knapsack batch router
# ---------------------------------------------------------------------------
def greedy_knapsack(pred_pc, budget_cap):
    """Greedy multiple-choice knapsack.

    pred_pc : (N, 3) predicted P(correct | pred_d, tier)
    budget_cap : total monetary budget for this batch

    Returns assignments: (N,) int in {0, 1, 2} (Haiku, Sonnet, Opus).
    """
    n = pred_pc.shape[0]
    assignments = np.zeros(n, dtype=int)
    remaining = budget_cap - n * COSTS[0]   # pre-pay Haiku for all queries

    if remaining <= 0:
        return assignments

    idx = np.arange(n)

    # Upgrade H->S: marginal cost 4, gain pred_pc[:,1] - pred_pc[:,0]
    gain_hs = np.maximum(pred_pc[:, 1] - pred_pc[:, 0], 0.0)
    eff_hs = gain_hs / (COSTS[1] - COSTS[0])   # gain per dollar

    # Upgrade H->O: marginal cost 24, gain pred_pc[:,2] - pred_pc[:,0]
    gain_ho = np.maximum(pred_pc[:, 2] - pred_pc[:, 0], 0.0)
    eff_ho = gain_ho / (COSTS[2] - COSTS[0])

    # Combine into one sorted candidate list
    all_eff = np.concatenate([eff_hs, eff_ho])
    all_target = np.concatenate([np.ones(n, dtype=int), np.full(n, 2, dtype=int)])
    all_query = np.concatenate([idx, idx])

    order = np.argsort(-all_eff)   # descending efficiency

    for k in order:
        i = int(all_query[k])
        target = int(all_target[k])
        if assignments[i] >= target:
            continue
        # Marginal cost from CURRENT tier (handles H->S already done, then S->O)
        actual_cost = COSTS[target] - COSTS[assignments[i]]
        if actual_cost <= remaining:
            remaining -= actual_cost
            assignments[i] = target

    return assignments


def run_batch_router(pred_d, outcomes, opus_acc):
    """Sweep budget levels; return best (min cost) assignment meeting quality tolerance."""
    n = len(pred_d)
    pred_pc = p_correct_matrix(pred_d)
    opus_cost = float(n * COSTS[2])
    target_acc = opus_acc - QUALITY_TOL

    best_cost = opus_cost
    best_result = None

    # Budget sweep from all-Haiku to all-Opus in steps of 100 (=0.4% of opus_cost)
    budgets = np.arange(n * COSTS[0], opus_cost + 1, 100.0)
    budgets = np.unique(np.append(budgets, opus_cost))

    for budget_cap in budgets:
        asgn = greedy_knapsack(pred_pc, budget_cap)
        cost = float(np.sum(COSTS[asgn]))
        correct = sum(float(outcomes[t][asgn == t].sum()) for t in range(3))
        acc = correct / n

        if acc >= target_acc and cost < best_cost:
            best_cost = cost
            best_result = {
                "batch_cost": cost,
                "batch_acc": acc,
                "batch_reduction_vs_opus_pct": (1.0 - cost / opus_cost) * 100.0,
                "haiku_frac": float((asgn == 0).mean()),
                "sonnet_frac": float((asgn == 1).mean()),
                "opus_frac": float((asgn == 2).mean()),
            }

    if best_result is None:
        best_result = {
            "batch_cost": opus_cost,
            "batch_acc": opus_acc,
            "batch_reduction_vs_opus_pct": 0.0,
            "haiku_frac": 0.0,
            "sonnet_frac": 0.0,
            "opus_frac": 1.0,
        }

    return best_result, opus_cost


# ---------------------------------------------------------------------------
# Independent threshold router
# ---------------------------------------------------------------------------
def run_threshold_router(pred_d, outcomes, opus_acc):
    """Sweep (t_haiku, t_sonnet) pairs; return best min-cost meeting quality tolerance."""
    n = len(pred_d)
    opus_cost = float(n * COSTS[2])
    target_acc = opus_acc - QUALITY_TOL

    best_cost = opus_cost
    best_result = None

    for t_h in np.arange(0.05, 0.625, 0.025):
        for t_s in np.arange(t_h + 0.025, 0.85, 0.025):
            haiku_m = pred_d < t_h
            sonnet_m = (pred_d >= t_h) & (pred_d < t_s)
            opus_m = pred_d >= t_s

            cost = float(
                haiku_m.sum() * COSTS[0]
                + sonnet_m.sum() * COSTS[1]
                + opus_m.sum() * COSTS[2]
            )
            correct = (
                float(outcomes[0][haiku_m].sum())
                + float(outcomes[1][sonnet_m].sum())
                + float(outcomes[2][opus_m].sum())
            )
            acc = correct / n

            if acc >= target_acc and cost < best_cost:
                best_cost = cost
                best_result = {
                    "indep_cost": cost,
                    "indep_acc": acc,
                    "indep_reduction_vs_opus_pct": (1.0 - cost / opus_cost) * 100.0,
                    "t_haiku": round(float(t_h), 3),
                    "t_sonnet": round(float(t_s), 3),
                    "haiku_frac": float(haiku_m.mean()),
                    "sonnet_frac": float(sonnet_m.mean()),
                    "opus_frac": float(opus_m.mean()),
                }

    if best_result is None:
        best_result = {
            "indep_cost": opus_cost,
            "indep_acc": opus_acc,
            "indep_reduction_vs_opus_pct": 0.0,
            "t_haiku": 0.0,
            "t_sonnet": 1.0,
            "haiku_frac": 0.0,
            "sonnet_frac": 0.0,
            "opus_frac": 1.0,
        }

    return best_result, opus_cost


# ---------------------------------------------------------------------------
# Full experiment — one seed
# ---------------------------------------------------------------------------
def run_full(seed):
    rng = np.random.RandomState(seed)
    batch_results = []

    for batch_idx in range(N_BATCHES):
        # Shared draws for this batch
        d = rng.beta(2, 3, size=N_QUERIES)
        noise = rng.normal(0, NOISE_STD, size=N_QUERIES)
        pred_d = np.clip(d + noise, 0, 1)   # both routers see this

        # Realise outcomes for each tier (true difficulty)
        true_pc = p_correct_matrix(d)
        outcomes = [
            (rng.random(N_QUERIES) < true_pc[:, t]).astype(float)
            for t in range(3)
        ]

        opus_acc = float(outcomes[2].mean())

        batch_res, opus_cost = run_batch_router(pred_d, outcomes, opus_acc)
        indep_res, _ = run_threshold_router(pred_d, outcomes, opus_acc)

        batch_cost = batch_res["batch_cost"]
        indep_cost = indep_res["indep_cost"]

        cost_reduction = (
            (1.0 - batch_cost / indep_cost) * 100.0 if indep_cost > 0 else 0.0
        )

        batch_results.append({
            "batch_idx": batch_idx,
            "cost_reduction_vs_independent_routing_pct": round(cost_reduction, 4),
            "independent_reduction_vs_opus_pct": round(
                indep_res["indep_reduction_vs_opus_pct"], 4
            ),
            "batch_reduction_vs_opus_pct": round(
                batch_res["batch_reduction_vs_opus_pct"], 4
            ),
            "batch_cost": round(batch_cost, 2),
            "indep_cost": round(indep_cost, 2),
            "opus_cost": round(opus_cost, 2),
            "batch_acc": round(batch_res["batch_acc"], 4),
            "indep_acc": round(indep_res["indep_acc"], 4),
            "opus_acc": round(opus_acc, 4),
            "batch_haiku_frac": round(batch_res["haiku_frac"], 4),
            "batch_sonnet_frac": round(batch_res["sonnet_frac"], 4),
            "batch_opus_frac": round(batch_res["opus_frac"], 4),
            "indep_t_haiku": indep_res["t_haiku"],
            "indep_t_sonnet": indep_res["t_sonnet"],
        })

    def mean_key(k):
        return round(float(np.mean([r[k] for r in batch_results])), 4)

    return {
        "seed": seed,
        "cost_reduction_vs_independent_routing_pct": mean_key(
            "cost_reduction_vs_independent_routing_pct"
        ),
        "independent_reduction_vs_opus_pct": mean_key("independent_reduction_vs_opus_pct"),
        "batch_reduction_vs_opus_pct": mean_key("batch_reduction_vs_opus_pct"),
        "batch_acc_mean": mean_key("batch_acc"),
        "indep_acc_mean": mean_key("indep_acc"),
        "opus_acc_mean": mean_key("opus_acc"),
        "per_batch": batch_results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="EXP-003: Batch Knapsack Routing")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--config", choices=["sanity", "full"], required=True)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    t0 = time.time()

    if args.config == "sanity":
        rng = np.random.RandomState(args.seed)
        result = run_sanity(rng)
    else:
        result = run_full(args.seed)

    result["wall_seconds"] = round(time.time() - t0, 2)
    result["config"] = args.config
    result["seed"] = args.seed

    line = json.dumps(result)
    print(line)

    if args.out:
        with open(args.out, "a") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    main()
