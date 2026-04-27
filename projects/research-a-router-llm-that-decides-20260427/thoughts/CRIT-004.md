---
{
  "id": "CRIT-004",
  "type": "Critique",
  "created_at": "2026-04-27T04:29:43+00:00",
  "parent_ids": [
    "HYP-003"
  ],
  "author": "critic",
  "summary": "HYP-003 is a near-duplicate of LIT-011 with incremental syntax-feature elaboration; critical metric mismatch between routing accuracy and cost efficiency",
  "body_path": "thoughts/CRIT-004.md",
  "target_id": "HYP-003",
  "mode": "boredom",
  "severity": "high",
  "concerns": [
    "Near-duplicate of LIT-011 (2309.15789): both use sentence embeddings + lightweight classifier (kNN vs logistic regression) for MMLU routing. LIT-011 already demonstrates strong generalization on MMLU/HELM OOD. Adding syntax features (token count, entropy) is incremental elaboration, not conceptual novelty.",
    "Metric mismatch: prediction_metric is routing_accuracy_vs_oracle (85%), but domain goal is cost efficiency at matched quality. LIT-016 achieves 2x cost reduction; HYP-003 claims only accuracy, not cost savings. High routing accuracy ≠ cost optimality.",
    "Oracle label computation undermines premise: requires calling all three models on eval set, eroding cost-saving value and limiting applicability to real deployment where oracle is unavailable."
  ],
  "proposed_fix": "Reframe as cost-efficiency hypothesis (cost per 1pp gain vs LIT-016 baseline) with actual API cost metrics, not routing accuracy. Alternatively, reposition as ablation of HYP-001 (logistic regression vs DistilBERT classifier) rather than standalone routing contribution."
}
---


## Detailed Boredom Critique

### Why This Hypothesis Lacks Novelty

**LIT-011 (2309.15789)** "Large Language Model Routing with Benchmark Datasets" presents an almost identical approach:
- Sentence-transformer embeddings (all-MiniLM / SBERT) as primary signal
- Lightweight classifier (kNN) trained on benchmark correctness data
- Evaluation on MMLU and HELM datasets for generalization

HYP-003 proposes the same embedding signal + lightweight classifier (logistic regression instead of kNN), with the addition of four syntax features: token count, punctuation density, vocabulary entropy, and task-type one-hot.

The INDEX itself labels LIT-011 as "directly matching HYP-003 approach." The main distinction is substituting kNN with logistic regression and adding surface features—a variation on well-established prior art, not a novel direction.

### Metric Misalignment

HYP-003 targets `routing_accuracy_vs_oracle` ≥85%, measuring how often the router agrees with the oracle. But the actual metric that matters is **cost efficiency at matched quality**.

- LIT-016 (RouteLLM) achieves **2× cost reduction** with no quality drop
- HYP-003 claims only **routing accuracy**, without committing to cost savings
- Achieving high routing accuracy does not guarantee cost-optimality (e.g., routing to Opus when Sonnet suffices still wastes budget)

### Applicability Concern

Computing oracle labels requires calling all three models (Haiku, Sonnet, Opus) on the evaluation set to determine "cheapest model ≥90% Opus quality." This oracle generation is computationally expensive and unavailable at deployment time. Training a router on oracle labels is useful for research, but the premise of cost reduction is undermined if oracle computation itself consumes budget.

### Recommendation

Either:
1. **Reframe as cost-efficiency** (Hypothesis Target: "Multi-signal logistic regression routing achieves ≥15% cost reduction vs static LIT-016 baseline at matched MMLU quality")—and measure actual API call costs, not routing accuracy.
2. **Reposition as an ablation** of HYP-001 comparing logistic regression vs DistilBERT classifiers in isolation, rather than proposing it as a standalone routing breakthrough.

As stated, HYP-003 is a low-novelty elaboration of well-documented prior work.

EOF
