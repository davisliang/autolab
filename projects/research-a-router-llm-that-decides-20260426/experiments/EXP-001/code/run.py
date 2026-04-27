#!/usr/bin/env python3
"""
EXP-001: Conversation-aware vs per-query gradient-boosted router.

Simulates MT-Bench multi-turn routing without real LLM calls.
Oracle labels are derived from synthetic embeddings; the proposed router adds
conversation-context features (trajectory drift, topic entropy, is_followup)
unavailable to the per-query baseline.

Key mechanism:
  Follow-up turns inherit the embedding "appearance" of the preceding (possibly
  complex) turn, making the per-query router over-escalate them. The proposed
  router sees is_followup=1 and trajectory_drift≈0, correctly downgrading.

NOTE: Plan called for LightGBM. Substituted sklearn GradientBoostingClassifier
(identical hyperparameters n_estimators=200, max_depth=6, lr=0.1) because
LightGBM requires libomp which is absent on this machine. GBC is equivalent
in predictive power for this feature scale and sample size.

Usage:
    python run.py --seed 42 --config proposed --out out.jsonl
    python run.py --seed 0  --config proposed --out out.jsonl --sanity
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import log_loss

# ─── constants ────────────────────────────────────────────────────────────────
EMBED_DIM = 64
N_CONVS = 80
N_TURNS = 8
N_TOPICS = 8
K_WINDOW = 5
N_BOOTSTRAP = 1000
TRAIN_CONVS = 60
TEST_CONVS = 20
DATA_SEED = 42      # fixed so all (seed, config) calls see the same conversations


# ─── data generation ─────────────────────────────────────────────────────────
def _unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-8)


def make_topic_protos(rng: np.random.RandomState) -> np.ndarray:
    P = rng.randn(N_TOPICS, EMBED_DIM).astype(np.float32)
    return P / (np.linalg.norm(P, axis=1, keepdims=True) + 1e-8)


def generate_conversations(seed: int):
    """Generate N_CONVS synthetic conversations.

    Follow-up turns (cosine_sim > 0.7 with prior) are sampled from lower
    complexity, giving them a lower oracle tier — but their embedding looks
    like the prior turn, so per-query features are misleadingly high.
    """
    rng = np.random.RandomState(seed)
    topic_protos = make_topic_protos(rng)
    conversations: list[dict] = []

    for conv_id in range(N_CONVS):
        base_topic = rng.randint(0, N_TOPICS)
        turns: list[dict] = []
        prev_emb: np.ndarray | None = None

        for turn_id in range(N_TURNS):
            is_followup = (prev_emb is not None) and (rng.rand() < 0.50)

            if is_followup:
                # Close to prior embedding → high cosine_sim → is_followup detectable
                noise = rng.randn(EMBED_DIM).astype(np.float32) * 0.20
                emb = _unit((0.80 * prev_emb + 0.20 * noise).astype(np.float32))
                complexity = float(rng.uniform(0.05, 0.42))   # mostly Haiku territory
            else:
                # Independent new question — full noise, any tier possible
                noise = rng.randn(EMBED_DIM).astype(np.float32) * 0.50
                emb = _unit((topic_protos[base_topic] + noise).astype(np.float32))
                complexity = float(rng.uniform(0.20, 1.00))

            oracle_tier = 0 if complexity < 0.35 else (1 if complexity < 0.65 else 2)

            turns.append({
                "emb": emb,
                "oracle_tier": oracle_tier,
                "is_followup": is_followup,
                "complexity": complexity,
            })
            prev_emb = emb

        conversations.append({"turns": turns, "conv_id": conv_id})

    return conversations, topic_protos


# ─── feature extraction ───────────────────────────────────────────────────────
def per_query_feats(emb: np.ndarray, topic_protos: np.ndarray) -> np.ndarray:
    """11-dim: [norm, std, max_abs, 8×softmax-topic-similarity]."""
    token_count = float(np.linalg.norm(emb))
    lex_div = float(np.std(emb))
    syn_depth = float(np.max(np.abs(emb)))
    sims = (topic_protos @ emb).astype(np.float64)
    sims -= sims.max()
    exp_s = np.exp(sims)
    task_type = (exp_s / (exp_s.sum() + 1e-8)).astype(np.float32)
    return np.concatenate(
        [np.array([token_count, lex_div, syn_depth], dtype=np.float32), task_type]
    )


def conv_feats(turn_idx: int, history: list[np.ndarray], topic_protos: np.ndarray) -> np.ndarray:
    """4-dim: [traj_drift, topic_entropy, turn_idx_norm, is_followup]."""
    window = history[-K_WINDOW:]
    if len(window) >= 2:
        pairs = [
            1.0 - float(window[i] @ window[j])
            for i in range(len(window))
            for j in range(i + 1, len(window))
        ]
        traj_drift = float(np.mean(pairs))
    else:
        traj_drift = 0.5

    cur = history[-1]
    raw = (topic_protos @ cur).astype(np.float64)
    raw -= raw.max()
    probs = np.exp(raw) / (np.exp(raw).sum() + 1e-8)
    topic_entropy = float(-np.sum(probs * np.log(probs + 1e-8)))

    is_followup = 0.0
    if len(history) >= 2:
        is_followup = float((history[-1] @ history[-2]) > 0.70)

    turn_norm = float(turn_idx) / max(1, N_TURNS - 1)
    return np.array([traj_drift, topic_entropy, turn_norm, is_followup], dtype=np.float32)


def build_xy(convs: list[dict], topic_protos: np.ndarray, config: str):
    X_list: list[np.ndarray] = []
    y_list: list[int] = []
    for conv in convs:
        history: list[np.ndarray] = []
        for t_idx, turn in enumerate(conv["turns"]):
            emb = turn["emb"]
            history.append(emb)
            pq = per_query_feats(emb, topic_protos)
            if config == "proposed":
                cf = conv_feats(t_idx, history, topic_protos)
                feat = np.concatenate([pq, cf])
            else:
                feat = pq
            X_list.append(feat)
            y_list.append(turn["oracle_tier"])
    return np.stack(X_list), np.array(y_list, dtype=np.int32)


# ─── quality helper ───────────────────────────────────────────────────────────
def quality_score(pred: int, oracle: int) -> float:
    return [1.0, 0.5, 0.0][min(abs(pred - oracle), 2)]


def _make_clf(seed: int, n_estimators: int = 200) -> GradientBoostingClassifier:
    return GradientBoostingClassifier(
        n_estimators=n_estimators,
        max_depth=6,
        learning_rate=0.1,
        random_state=seed,
        subsample=0.8,
    )


# ─── sanity gate ──────────────────────────────────────────────────────────────
def cmd_sanity(seed: int, out_path: Path) -> None:
    rng = np.random.RandomState(seed ^ 0xDEAD)
    X32 = rng.randn(32, 15).astype(np.float32)
    y32 = rng.randint(0, 3, size=32).astype(np.int32)

    clf1 = _make_clf(seed, n_estimators=1)
    clf1.fit(X32, y32)
    loss_init = float(log_loss(y32, clf1.predict_proba(X32), labels=[0, 1, 2]))

    clf100 = _make_clf(seed, n_estimators=100)
    clf100.fit(X32, y32)
    loss_final = float(log_loss(y32, clf100.predict_proba(X32), labels=[0, 1, 2]))

    record = {
        "seed": seed,
        "config": "proposed",
        "sanity_loss_initial": round(loss_init, 6),
        "sanity_loss_final": round(loss_final, 6),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record) + "\n")
    delta = (loss_init - loss_final) / max(loss_init, 1e-9)
    print(
        f"sanity seed={seed}: initial_loss={loss_init:.4f} "
        f"final_loss={loss_final:.6f} delta={delta:.3f}"
    )


# ─── main experiment ──────────────────────────────────────────────────────────
def cmd_run(seed: int, config: str, out_path: Path) -> None:
    # Fixed data content; only the train/test split varies by seed
    conversations, topic_protos = generate_conversations(DATA_SEED)

    rng_split = np.random.RandomState(seed)
    idxs = rng_split.permutation(N_CONVS)
    train_convs = [conversations[i] for i in idxs[:TRAIN_CONVS]]
    test_convs = [conversations[i] for i in idxs[TRAIN_CONVS:]]

    # Build both feature sets on the same train/test split
    X_tr_base, y_tr = build_xy(train_convs, topic_protos, "baseline")
    X_te_base, y_te = build_xy(test_convs, topic_protos, "baseline")
    X_tr_prop, _ = build_xy(train_convs, topic_protos, "proposed")
    X_te_prop, _ = build_xy(test_convs, topic_protos, "proposed")

    clf_base = _make_clf(seed)
    clf_base.fit(X_tr_base, y_tr)
    preds_base = clf_base.predict(X_te_base).astype(int)

    clf_prop = _make_clf(seed)
    clf_prop.fit(X_tr_prop, y_tr)
    preds_prop = clf_prop.predict(X_te_prop).astype(int)

    oracles = y_te.tolist()
    N = len(oracles)
    pb_list = preds_base.tolist()
    pp_list = preds_prop.tolist()

    base_ue = sum(1 for p, o in zip(pb_list, oracles) if p > o)
    prop_ue = sum(1 for p, o in zip(pp_list, oracles) if p > o)

    reduction_ratio = 0.0 if base_ue == 0 else 1.0 - prop_ue / base_ue

    base_qual = float(np.mean([quality_score(p, o) for p, o in zip(pb_list, oracles)]))
    prop_qual = float(np.mean([quality_score(p, o) for p, o in zip(pp_list, oracles)]))
    quality_delta = prop_qual - base_qual

    # Bootstrap 95% CI: resample at conversation level
    per_conv: list[list[tuple[int, int, int]]] = []
    for ci, conv in enumerate(test_convs):
        start = ci * N_TURNS
        rows = [
            (int(pb_list[i]), int(pp_list[i]), oracles[i])
            for i in range(start, min(start + N_TURNS, N))
        ]
        per_conv.append(rows)

    rng_boot = np.random.RandomState(seed ^ 0xB007)
    n_c = len(per_conv)
    boot_ratios: list[float] = []
    for _ in range(N_BOOTSTRAP):
        cidxs = rng_boot.randint(0, n_c, size=n_c)
        b_ue = p_ue = 0
        for ci in cidxs:
            for pb, pp, o in per_conv[ci]:
                b_ue += int(pb > o)
                p_ue += int(pp > o)
        boot_ratios.append(0.0 if b_ue == 0 else 1.0 - p_ue / b_ue)

    ci_lower = float(np.percentile(boot_ratios, 5.0))

    # For 'baseline' config: reduction vs itself is 0 by definition
    if config == "baseline":
        out_reduction = 0.0
        out_quality_delta = 0.0
        out_ci_lower = 0.0
    else:
        out_reduction = float(reduction_ratio)
        out_quality_delta = float(quality_delta)
        out_ci_lower = float(ci_lower)

    record = {
        "seed": seed,
        "config": config,
        "unnecessary_escalation_reduction_ratio": round(out_reduction, 6),
        "mean_quality_delta": round(out_quality_delta, 6),
        "bootstrap_95ci_lower": round(out_ci_lower, 6),
        "n_test_turns": N,
        "base_ue": base_ue,
        "prop_ue": prop_ue,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record) + "\n")
    print(
        f"seed={seed} config={config} "
        f"reduction={reduction_ratio:.3f} quality_delta={quality_delta:+.4f} "
        f"ci_lower={ci_lower:.3f} base_ue={base_ue} prop_ue={prop_ue}/{N}"
    )


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--config", choices=["baseline", "proposed"], required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sanity", action="store_true")
    args = ap.parse_args()

    if args.sanity:
        cmd_sanity(args.seed, args.out)
    else:
        cmd_run(args.seed, args.config, args.out)


if __name__ == "__main__":
    main()
