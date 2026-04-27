#!/usr/bin/env python3
"""EXP-002: Selective Speculation — Hybrid Pre-Screen + Output-Verified Cascade.

Materially different from EXP-001: instead of always speculating (Haiku on every
query), a cheap input-feature pre-screen triages queries into three zones:
  - Easy → Haiku direct (no judge overhead)
  - Ambiguous → Haiku + judge → accept or escalate to Sonnet
  - Hard → Sonnet direct (no Haiku overhead)

This eliminates the structural overhead that killed EXP-001.

Usage:
  python run.py --seed 42 --config proposed --out results.jsonl
  python run.py --seed 42 --config baseline --out results.jsonl
  python run.py --seed 42 --config sanity   --out results.jsonl
  python run.py --seed 42 --config full     --out results.jsonl
"""

import argparse
import json
import time

import numpy as np


# ---------------------------------------------------------------------------
# Constants (matched to EXP-001 for comparability)
# ---------------------------------------------------------------------------
N_QUESTIONS = 1319
HAIKU_COST = 1.0
JUDGE_COST = 0.2
SONNET_COST = 5.0
QUALITY_TOLERANCE_PP = 2.0

HAIKU_MIDPOINT = 0.35
SONNET_MIDPOINT = 0.60
SLOPE = 0.05


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def p_correct(difficulty, midpoint):
    return sigmoid(-(difficulty - midpoint) / SLOPE)


# ---------------------------------------------------------------------------
# Simulation core
# ---------------------------------------------------------------------------
def simulate(rng, config):
    difficulty = rng.beta(2, 3, size=N_QUESTIONS)
    haiku_prob = p_correct(difficulty, HAIKU_MIDPOINT)
    sonnet_prob = p_correct(difficulty, SONNET_MIDPOINT)
    haiku_correct = rng.random(N_QUESTIONS) < haiku_prob
    sonnet_correct = rng.random(N_QUESTIONS) < sonnet_prob

    sonnet_only_acc = sonnet_correct.mean()
    sonnet_only_cost = SONNET_COST * N_QUESTIONS

    if config == "proposed":
        return run_selective_speculation(
            rng, difficulty, haiku_correct, sonnet_correct,
            sonnet_only_acc, sonnet_only_cost,
        )
    elif config == "baseline":
        return run_input_feature_router(
            rng, difficulty, haiku_correct, sonnet_correct,
            sonnet_only_acc, sonnet_only_cost,
        )
    else:
        raise ValueError(f"Unknown config: {config}")


def run_selective_speculation(rng, difficulty, haiku_correct, sonnet_correct,
                              sonnet_only_acc, sonnet_only_cost):
    """Selective speculation: pre-screen -> 3 zones."""
    noise = rng.normal(0, 0.10, size=N_QUESTIONS)
    estimated_diff = np.clip(difficulty + noise, 0, 1)

    judge_tpr = 0.80
    judge_fpr = 0.05

    best_result = None
    best_savings = -999

    for low_t in np.arange(0.15, 0.45, 0.05):
        for band_width in np.arange(0.10, 0.45, 0.05):
            high_t = low_t + band_width
            if high_t > 0.75:
                continue

            easy_mask = estimated_diff < low_t
            hard_mask = estimated_diff >= high_t
            ambig_mask = ~easy_mask & ~hard_mask

            n_easy = easy_mask.sum()
            n_hard = hard_mask.sum()
            n_ambig = ambig_mask.sum()

            # Easy zone: Haiku direct
            easy_cost = n_easy * HAIKU_COST
            easy_correct = haiku_correct[easy_mask].sum()

            # Hard zone: Sonnet direct
            hard_cost = n_hard * SONNET_COST
            hard_correct = sonnet_correct[hard_mask].sum()

            # Ambiguous zone: Haiku + judge -> accept or escalate
            ambig_haiku_ok = haiku_correct[ambig_mask]
            judge_accept = np.zeros(n_ambig, dtype=bool)
            for i in range(n_ambig):
                if ambig_haiku_ok[i]:
                    judge_accept[i] = rng.random() < judge_tpr
                else:
                    judge_accept[i] = rng.random() < judge_fpr

            n_accepted = judge_accept.sum()
            n_escalated = n_ambig - n_accepted

            ambig_cost = n_ambig * (HAIKU_COST + JUDGE_COST) + n_escalated * SONNET_COST
            ambig_correct = (
                haiku_correct[ambig_mask][judge_accept].sum()
                + sonnet_correct[ambig_mask][~judge_accept].sum()
            )

            total_cost = easy_cost + hard_cost + ambig_cost
            total_correct = easy_correct + hard_correct + ambig_correct
            accuracy = total_correct / N_QUESTIONS
            acc_delta = (accuracy - sonnet_only_acc) * 100

            if acc_delta < -QUALITY_TOLERANCE_PP:
                continue

            savings_pp = (1 - total_cost / sonnet_only_cost) * 100

            if savings_pp > best_savings:
                best_savings = savings_pp
                best_result = {
                    "proposed_savings_pp": round(savings_pp, 4),
                    "accuracy_delta_vs_sonnet_pp": round(acc_delta, 4),
                    "ambiguous_zone_fraction": round(n_ambig / N_QUESTIONS, 4),
                    "easy_fraction": round(n_easy / N_QUESTIONS, 4),
                    "hard_fraction": round(n_hard / N_QUESTIONS, 4),
                    "low_threshold": round(float(low_t), 2),
                    "high_threshold": round(float(high_t), 2),
                    "n_accepted": int(n_accepted),
                    "n_escalated": int(n_escalated),
                }

    if best_result is None:
        best_result = {
            "proposed_savings_pp": 0.0,
            "accuracy_delta_vs_sonnet_pp": -99.0,
            "ambiguous_zone_fraction": 0.0,
            "easy_fraction": 0.0,
            "hard_fraction": 0.0,
            "low_threshold": 0.0,
            "high_threshold": 0.0,
            "n_accepted": 0,
            "n_escalated": 0,
        }

    return best_result


def run_input_feature_router(rng, difficulty, haiku_correct, sonnet_correct,
                              sonnet_only_acc, sonnet_only_cost):
    """Pure input-feature router (binary Haiku/Sonnet). Same as EXP-001 baseline."""
    noise = rng.normal(0, 0.10, size=N_QUESTIONS)
    estimated_diff = np.clip(difficulty + noise, 0, 1)

    best_result = None
    best_savings = -999

    for threshold in np.arange(0.10, 0.56, 0.01):
        route_haiku = estimated_diff < threshold
        route_sonnet = ~route_haiku

        total_cost = route_haiku.sum() * HAIKU_COST + route_sonnet.sum() * SONNET_COST
        total_correct = (
            haiku_correct[route_haiku].sum()
            + sonnet_correct[route_sonnet].sum()
        )
        accuracy = total_correct / N_QUESTIONS
        acc_delta = (accuracy - sonnet_only_acc) * 100

        if acc_delta < -QUALITY_TOLERANCE_PP:
            continue

        savings_pp = (1 - total_cost / sonnet_only_cost) * 100

        if savings_pp > best_savings:
            best_savings = savings_pp
            best_result = {
                "baseline_savings_pp": round(savings_pp, 4),
                "accuracy_delta_vs_sonnet_pp": round(acc_delta, 4),
                "threshold": round(float(threshold), 2),
                "haiku_fraction": round(float(route_haiku.mean()), 4),
            }

    if best_result is None:
        best_result = {
            "baseline_savings_pp": 0.0,
            "accuracy_delta_vs_sonnet_pp": -99.0,
            "threshold": 0.0,
            "haiku_fraction": 0.0,
        }

    return best_result


# ---------------------------------------------------------------------------
# Sanity gate
# ---------------------------------------------------------------------------
def run_sanity(rng):
    """Train logistic regression on 32 examples, verify loss drops >=50%."""
    n = 32
    difficulty = rng.uniform(0.0, 1.0, size=n)  # wider spread for stronger signal
    labels = (rng.random(n) < p_correct(difficulty, HAIKU_MIDPOINT)).astype(float)

    # Features: normalized difficulty (noisy)
    x_raw = difficulty + rng.normal(0, 0.05, size=n)
    x_mean, x_std = x_raw.mean(), x_raw.std() + 1e-8
    X = (x_raw - x_mean) / x_std  # normalize for stable convergence

    w, b = 0.0, 0.0
    lr = 2.0

    def cross_entropy(w, b):
        logits = w * X + b
        probs = sigmoid(logits)
        probs = np.clip(probs, 1e-7, 1 - 1e-7)
        return -np.mean(labels * np.log(probs) + (1 - labels) * np.log(1 - probs))

    loss_before = cross_entropy(w, b)

    for _ in range(1000):
        logits = w * X + b
        preds = sigmoid(logits)
        errors = preds - labels
        grad_w = np.mean(errors * X)
        grad_b = np.mean(errors)
        w -= lr * grad_w
        b -= lr * grad_b

    loss_after = cross_entropy(w, b)
    drop_pct = (loss_before - loss_after) / loss_before * 100

    return {
        "loss_before": round(float(loss_before), 4),
        "loss_after": round(float(loss_after), 4),
        "loss_drop_pct": round(float(drop_pct), 2),
        "sanity_pass": bool(drop_pct >= 50.0),
    }


# ---------------------------------------------------------------------------
# Full experiment
# ---------------------------------------------------------------------------
def run_full(seed):
    """Run one seed: proposed selective speculation vs baseline input-feature router."""
    rng_proposed = np.random.RandomState(seed)
    rng_baseline = np.random.RandomState(seed)

    proposed = simulate(rng_proposed, "proposed")
    baseline = simulate(rng_baseline, "baseline")

    delta = proposed["proposed_savings_pp"] - baseline["baseline_savings_pp"]

    return {
        "seed": seed,
        "cost_savings_pp_vs_feature_router": round(delta, 4),
        "proposed_savings_pp": proposed["proposed_savings_pp"],
        "baseline_savings_pp": baseline["baseline_savings_pp"],
        "accuracy_delta_vs_sonnet_pp": proposed["accuracy_delta_vs_sonnet_pp"],
        "ambiguous_zone_fraction": proposed["ambiguous_zone_fraction"],
        "easy_fraction": proposed.get("easy_fraction", 0),
        "hard_fraction": proposed.get("hard_fraction", 0),
        "baseline_haiku_fraction": baseline.get("haiku_fraction", 0),
        "proposed_low_threshold": proposed.get("low_threshold", 0),
        "proposed_high_threshold": proposed.get("high_threshold", 0),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="EXP-002: Selective Speculation")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--config", choices=["proposed", "baseline", "sanity", "full"],
                        required=True)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    t0 = time.time()

    if args.config == "sanity":
        rng = np.random.RandomState(args.seed)
        result = run_sanity(rng)
    elif args.config == "full":
        result = run_full(args.seed)
    else:
        rng = np.random.RandomState(args.seed)
        result = simulate(rng, args.config)

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
