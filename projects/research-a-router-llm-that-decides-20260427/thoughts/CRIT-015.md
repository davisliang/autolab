---
{
  "id": "CRIT-015",
  "type": "Critique",
  "created_at": "2026-04-27T05:00:03+00:00",
  "parent_ids": [
    "HYP-007"
  ],
  "author": "screen-boredom",
  "summary": "HYP-007 is feature-engineering incrementalism: rolling history features add modest complexity without novel insight or strong baseline comparison",
  "body_path": "thoughts/CRIT-015.md",
  "target_id": "HYP-007",
  "mode": "boredom",
  "severity": "high"
}
---

## Concern: Straightforward Feature Engineering, Not Novel Mechanism

HYP-007 proposes adding rolling prior-turn difficulty features to a per-query router. This is a classical feature-engineering exercise without an underlying algorithmic novelty or theoretical insight. The literature (LIT-015, LIT-008) already validates that simple input-feature routers achieve 2–5× cost reduction; bolting on temporal smoothing is not conceptually new.

## Concern: Weak Prediction Target Relative to State-of-the-Art

The hypothesis predicts ≥15% reduction in strong-model calls vs. a per-query baseline. But:
- RouterBench (LIT-015) shows 2–5× cost reduction via pure embedding-based routing—a factor of 2–5 is far more dramatic than 15%.
- RouteLLM (LIT-008) achieves 2× cost savings on MMLU without history features.

A 15% improvement on top of an already-optimized router is marginal and does not justify the complexity of tracking multi-turn state.

## Concern: Artificial Evaluation Setting

- MMLU is not naturally multi-turn; simulating multi-turn artificially introduces a constraint.
- No evidence that real multi-turn conversations exhibit a stable "rolling difficulty" signal that would persist and generalize.
- Single-benchmark evaluation (simulated MMLU) is insufficient to validate a hypothesis about multi-turn routing.

## Concern: Missing Baseline Clarity

The hypothesis compares to "per-query router" but does not specify which one:
- Is it a DistilBERT baseline (like HYP-001)?
- Is it RouteLLM?
- Is it a learned model on the same feature set but without history?

Without a precise baseline and head-to-head ablation (history vs. no history, controlling for model capacity and training data), the contribution is underspecified.

## Concern: LIT-029 Insight Not Leveraged

LIT-029 establishes that quality estimator fidelity is the binding constraint in routing. HYP-007 does not justify why rolling history is a better quality estimator—it may just add noise. No theoretical or empirical argument for why history features would improve fidelity over a well-tuned input-only model.

## Proposed Fix

If HYP-007 is to proceed, it must:
1. **Reframe as a mechanism**, not feature engineering: articulate a specific hypothesis about how/why temporal patterns in multi-turn conversation should improve routing (e.g., "users naturally escalate difficulty; history captures this pattern").
2. **Strengthen the baseline**: measure cost reduction as absolute $ savings vs. cost-per-correct-answer, not just relative %.
3. **Real multi-turn evaluation**: use a true multi-turn dataset (e.g., multi-round dialogue or iterative problem-solving) where difficulty patterns are naturally present, not simulated.
4. **Ablation chain**: per-query → per-query + summary → per-query + rolling window. Show which temporal window length is critical.

**Severity: HIGH** — The hypothesis reads as incremental feature engineering with weak novelty and a prediction target well below published baselines. Not recommended for design phase without substantial reframing.
