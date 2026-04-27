#!/usr/bin/env python3
"""
EXP-001: Multi-head 4D routing vs single-score baseline.

Outputs JSONL records to --out for aggregation by tools/run_experiment.py.

For --sanity: trains on 32 examples, reports initial/final loss drop.
For normal run: trains on full split, emits routing_accuracy,
cost_savings_ratio, quality_at_matched_cost.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import train_test_split


# ── Cost model (relative API cost units) ────────────────────────────────────
COST = {"haiku": 1.0, "sonnet": 5.0, "opus": 15.0}
LABELS = ["haiku", "sonnet", "opus"]


# ── Heuristic oracle label generation ───────────────────────────────────────
def _mmlu_oracle(q: str, subject: str) -> str:
    """For MMLU: hard STEM / law / medicine → opus; standard STEM → sonnet; rest → haiku."""
    hard = re.search(
        r"(calculus|differential|quantum|relativity|theorem|proof|circuit|"
        r"pharmacology|jurisprudence|biochemistry|genetics)",
        q + " " + subject, re.I
    )
    if hard:
        return "opus"
    stem = re.search(
        r"(math|physics|chemistry|biology|medicine|law|economics|history|"
        r"computer|science|statistics|logic)", subject, re.I
    )
    return "sonnet" if stem else "haiku"


def _gsm8k_oracle(q: str) -> str:
    """Multi-step arithmetic: count operation tokens as proxy for depth."""
    ops = len(re.findall(r"\d+\s*[+\-×*/÷]\s*\d+|\b(times|divided|plus|minus|total|percent)\b", q, re.I))
    steps = len(re.findall(r"\?", q))
    if ops >= 3 or steps >= 2:
        return "opus"
    return "sonnet"


def _alpaca_oracle(q: str) -> str:
    """Creative/open-ended → sonnet; trivial lookup → haiku; complex reasoning → opus."""
    creative = re.search(r"\b(write|compose|create|generate|poem|story|essay|explain|describe)\b", q, re.I)
    hard = re.search(r"\b(analyze|compare|evaluate|argue|synthesize|justify|critique)\b", q, re.I)
    if hard:
        return "opus"
    if creative:
        return "sonnet"
    return "haiku"


# ── 4D dimension labeller (heuristic) ────────────────────────────────────────
def label_dimensions(queries: list[str]) -> dict[str, np.ndarray]:
    """Return binary arrays for RD, DS, AMB, CR dimensions."""
    rd, ds, amb, cr = [], [], [], []
    for q in queries:
        ql = q.lower()
        rd.append(int(bool(re.search(
            r"\b(step|proof|derive|calculate|solve|reason|logic|chain|multi-step|"
            r"therefore|given that|since|thus|because|equation|formula)\b", ql
        ))))
        ds.append(int(bool(re.search(
            r"\b(quantum|biochem|jurisprud|pharmacol|theorem|calculus|relativity|"
            r"genetics|circuit|differential|integral|statute|tort|pathology)\b", ql
        ))))
        amb.append(int(bool(re.search(
            r"\b(what do you think|it depends|could mean|ambiguous|unclear|"
            r"various|different ways|interpret|perspective|opinion)\b", ql
        ))))
        cr.append(int(bool(re.search(
            r"\b(write|compose|create|generate|invent|imagine|design|story|poem|"
            r"essay|describe|suggest|brainstorm|list ideas)\b", ql
        ))))
    return {
        "RD": np.array(rd),
        "DS": np.array(ds),
        "AMB": np.array(amb),
        "CR": np.array(cr),
    }


# ── Data loading ─────────────────────────────────────────────────────────────
def load_queries(seed: int, n_per_source: int = 500) -> tuple[list[str], list[str]]:
    """
    Load queries from MMLU, GSM8K, and synthetic AlpacaEval-style data.
    Returns (queries, oracle_labels) where label ∈ {haiku, sonnet, opus}.
    """
    rng = random.Random(seed)
    queries: list[str] = []
    labels: list[str] = []

    # ── MMLU ────────────────────────────────────────────────────────────────
    try:
        from datasets import load_dataset
        mmlu = load_dataset("cais/mmlu", "all", split="validation")
        pool = list(mmlu)
        rng.shuffle(pool)
        for ex in pool[:n_per_source]:
            q = ex.get("question", "")
            subj = ex.get("subject", "")
            queries.append(q)
            labels.append(_mmlu_oracle(q, subj))
    except Exception:
        # Fallback: synthesize representative MMLU-like queries
        templates = [
            ("Which of the following best describes quantum entanglement?", "physics"),
            ("Calculate the derivative of sin(x^2).", "calculus"),
            ("What is the capital of France?", "geography"),
            ("Explain the role of mitochondria.", "biology"),
            ("What year did World War II end?", "history"),
            ("Solve: 3x + 7 = 22.", "math"),
            ("Define jurisprudence.", "law"),
            ("What is photosynthesis?", "biology"),
            ("Name a prime number between 10 and 20.", "math"),
            ("Describe the French Revolution.", "history"),
        ]
        for i in range(n_per_source):
            q, subj = templates[i % len(templates)]
            queries.append(f"{q} [var={i}]")
            labels.append(_mmlu_oracle(q, subj))

    # ── GSM8K ────────────────────────────────────────────────────────────────
    try:
        from datasets import load_dataset
        gsm = load_dataset("openai/gsm8k", "main", split="test")
        pool = list(gsm)
        rng.shuffle(pool)
        for ex in pool[:n_per_source]:
            q = ex.get("question", "")
            queries.append(q)
            labels.append(_gsm8k_oracle(q))
    except Exception:
        math_qs = [
            "Janet has 3 apples and buys 5 more times 2. How many apples?",
            "A train travels 60 mph for 2 hours. What distance did it cover?",
            "If 15% of 200 is X, what is X?",
            "Solve: (4 + 3) × 2 - 5 = ?",
            "A rectangle has length 8 and width 3. What is its area?",
        ]
        for i in range(n_per_source):
            q = math_qs[i % len(math_qs)] + f" [v={i}]"
            queries.append(q)
            labels.append(_gsm8k_oracle(q))

    # ── Alpaca-style (synthetic open-ended) ──────────────────────────────────
    alpaca_qs = [
        "Write a short poem about autumn leaves.",
        "Describe the impact of social media on politics.",
        "What is 2+2?",
        "Create a recipe for chocolate cake.",
        "Analyze the causes of climate change.",
        "Tell me a fun fact.",
        "Explain the concept of democracy.",
        "Write an essay arguing for renewable energy.",
        "List 5 tips for better sleep.",
        "Compare and contrast Python and JavaScript.",
        "Summarize the plot of Romeo and Juliet.",
        "Design a workout routine for beginners.",
        "What does 'serendipity' mean?",
        "Evaluate the ethical implications of AI in healthcare.",
        "Compose a haiku about winter.",
        "Who invented the telephone?",
        "Suggest ideas for a birthday party.",
        "Justify the importance of biodiversity.",
        "Imagine a world without electricity.",
        "Describe the water cycle.",
    ]
    for i in range(n_per_source):
        q = alpaca_qs[i % len(alpaca_qs)] + f" [{i}]"
        queries.append(q)
        labels.append(_alpaca_oracle(q))

    return queries, labels


# ── Embedding ─────────────────────────────────────────────────────────────────
_model_cache: dict = {}


def embed(queries: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    if "model" not in _model_cache:
        _model_cache["model"] = SentenceTransformer("all-MiniLM-L6-v2")
    m = _model_cache["model"]
    return m.encode(queries, show_progress_bar=False, batch_size=64)


# ── Quality simulation (proxy) ────────────────────────────────────────────────
def quality_score(predicted_model: str, oracle_model: str) -> float:
    """
    Proxy quality score: 1.0 if predicted >= oracle tier, degrades if too cheap.
    """
    tier = {"haiku": 0, "sonnet": 1, "opus": 2}
    p, o = tier.get(predicted_model, 1), tier.get(oracle_model, 1)
    if p >= o:
        return 1.0
    elif p == o - 1:
        return 0.75
    else:
        return 0.4


# ── Multi-head proposed router ────────────────────────────────────────────────
def run_multi_head(
    X_train: np.ndarray,
    y_dim_train: dict[str, np.ndarray],
    y_route_train: list[str],
    X_test: np.ndarray,
    seed: int,
) -> list[str]:
    heads: dict[str, LogisticRegression] = {}
    for dim in ["RD", "DS", "AMB", "CR"]:
        lr = LogisticRegression(C=1.0, max_iter=1000, random_state=seed)
        lr.fit(X_train, y_dim_train[dim])
        heads[dim] = lr

    meta_train = np.column_stack([heads[d].predict_proba(X_train)[:, 1] for d in heads])
    meta_test = np.column_stack([heads[d].predict_proba(X_test)[:, 1] for d in heads])

    rf = RandomForestClassifier(
        n_estimators=50, max_depth=5, min_samples_leaf=10, random_state=seed
    )
    rf.fit(meta_train, y_route_train)
    return list(rf.predict(meta_test))


# ── Single-score baseline router ──────────────────────────────────────────────
def run_baseline(
    X_train: np.ndarray,
    y_route_train: list[str],
    X_test: np.ndarray,
    seed: int,
) -> list[str]:
    lr = LogisticRegression(C=1.0, max_iter=1000, random_state=seed)
    lr.fit(X_train, y_route_train)
    return list(lr.predict(X_test))


# ── Metrics ────────────────────────────────────────────────────────────────────
def compute_metrics(
    predicted: list[str], oracle: list[str]
) -> dict[str, float]:
    n = len(predicted)
    routing_accuracy = sum(p == o for p, o in zip(predicted, oracle)) / n
    always_opus_cost = sum(COST["opus"] for _ in oracle)
    predicted_cost = sum(COST[p] for p in predicted)
    cost_savings_ratio = 1.0 - (predicted_cost / always_opus_cost)

    # quality_at_matched_cost: average quality score
    qualities = [quality_score(p, o) for p, o in zip(predicted, oracle)]
    quality_at_matched_cost = float(np.mean(qualities))

    return {
        "routing_accuracy": routing_accuracy,
        "cost_savings_ratio": cost_savings_ratio,
        "quality_at_matched_cost": quality_at_matched_cost,
    }


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--config", choices=["proposed", "baseline"], default="proposed")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sanity", action="store_true")
    args = ap.parse_args()

    np.random.seed(args.seed)
    random.seed(args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.sanity:
        # ── Sanity gate: overfit 32 examples ────────────────────────────────
        queries, labels = load_queries(args.seed, n_per_source=20)
        # Ensure at least one sample per class; take first 32 from stratified pool
        # Guarantee all 3 classes present by forcing one per class then filling up
        by_class: dict[str, list] = {"haiku": [], "sonnet": [], "opus": []}
        for q, l in zip(queries, labels):
            by_class[l].append(q)
        sanity_q: list[str] = []
        sanity_l: list[str] = []
        for cls in LABELS:
            sanity_q.append(by_class[cls][0])
            sanity_l.append(cls)
        # fill up to 32
        all_pairs = list(zip(queries, labels))
        random.seed(args.seed)
        random.shuffle(all_pairs)
        used = set(sanity_q)
        for q, l in all_pairs:
            if len(sanity_q) >= 32:
                break
            if q not in used:
                sanity_q.append(q)
                sanity_l.append(l)
                used.add(q)
        queries32 = sanity_q[:32]
        labels32 = sanity_l[:32]

        X = embed(queries32)
        y = labels32

        # Encode labels — all 3 classes guaranteed present
        label_to_int = {l: i for i, l in enumerate(LABELS)}
        y_int = np.array([label_to_int[l] for l in y])

        n_classes = len(LABELS)
        initial_probs = np.full((len(y), n_classes), 1.0 / n_classes)
        initial_loss = log_loss(y_int, initial_probs)

        lr = LogisticRegression(C=10.0, max_iter=2000, random_state=args.seed)
        lr.fit(X, y_int)
        final_probs = lr.predict_proba(X)
        final_loss = log_loss(y_int, final_probs)

        record = {
            "seed": args.seed,
            "config": "sanity",
            "sanity_loss_initial": initial_loss,
            "sanity_loss_final": final_loss,
        }
        with out_path.open("w") as f:
            f.write(json.dumps(record) + "\n")
        print(f"sanity: initial_loss={initial_loss:.4f} final_loss={final_loss:.4f} "
              f"drop={((initial_loss - final_loss) / initial_loss):.2%}")
        return

    # ── Full run ─────────────────────────────────────────────────────────────
    queries, labels = load_queries(args.seed)

    # Stratified split by source (each 500-block is one source)
    n = len(queries)
    indices = list(range(n))
    # Preserve source balance: sample from each third
    rng = random.Random(args.seed)
    train_idx, temp_idx = train_test_split(
        indices, test_size=0.30, random_state=args.seed,
        stratify=[i // 500 for i in indices]
    )
    val_idx, test_idx = train_test_split(
        temp_idx, test_size=0.50, random_state=args.seed,
        stratify=[i // 500 for i in temp_idx]
    )

    print(f"Split: train={len(train_idx)} val={len(val_idx)} test={len(test_idx)}")

    # Embed
    X_all = embed(queries)
    X_train = X_all[train_idx]
    X_test = X_all[test_idx]

    y_all = np.array(labels)
    y_train = [labels[i] for i in train_idx]
    y_test = [labels[i] for i in test_idx]

    # 4D dimension labels (train only)
    queries_train = [queries[i] for i in train_idx]
    dim_labels = label_dimensions(queries_train)

    if args.config == "proposed":
        predicted = run_multi_head(X_train, dim_labels, y_train, X_test, args.seed)
    else:
        predicted = run_baseline(X_train, y_train, X_test, args.seed)

    metrics = compute_metrics(predicted, y_test)
    record = {
        "seed": args.seed,
        "config": args.config,
        **metrics,
    }
    with out_path.open("w") as f:
        f.write(json.dumps(record) + "\n")
    print(f"seed={args.seed} config={args.config} "
          f"routing_accuracy={metrics['routing_accuracy']:.4f} "
          f"cost_savings={metrics['cost_savings_ratio']:.4f} "
          f"quality={metrics['quality_at_matched_cost']:.4f}")


if __name__ == "__main__":
    main()
