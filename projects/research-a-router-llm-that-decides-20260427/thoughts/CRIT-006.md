---
{
  "id": "CRIT-006",
  "type": "Critique",
  "created_at": "2026-04-27T04:31:06+00:00",
  "parent_ids": [
    "HYP-006"
  ],
  "author": "critic",
  "summary": "HYP-006 is a direct, low-novelty transplant of established contextual-bandit online learning; predicts modest ≥15pp cost gain in a narrow MMLU→GSM8K shift with oracle reward signal",
  "body_path": "thoughts/CRIT-006.md",
  "target_id": "HYP-006",
  "mode": "boredom",
  "severity": "high"
}
---

# Critique: HYP-006 (Boredom Mode)

## Summary
HYP-006 proposes that a contextual-bandit router (LinUCB) adapting online from deployment outcomes achieves ≥15% additional cost reduction vs. a frozen static router on a distribution-shifted query stream (MMLU→GSM8K). While the hypothesis is technically sound and pre-registered, it exhibits high boredom risk: contextual bandits are an established ML technique, applying them to routing is a direct transplant with no algorithmic novelty, the ≥15pp cost bar is modest relative to existing work, the experiment uses a narrow single distribution shift with an unrealistic oracle reward signal, and the result (if positive) merely confirms known online-learning principles rather than discovering something surprising.

## Boredom Signals

### 1. **Low Algorithmic Novelty: Direct Transplant of Established Technique**
Contextual multi-armed bandits (Thompson sampling, LinUCB, UCB) are foundational in online learning and widely deployed in recommendation systems. The hypothesis transplants LinUCB to LLM routing: a textbook application of an existing algorithm to a new domain. No novel bandit algorithm, no new regret bound, no algorithmic insight — purely a domain application.

### 2. **Modest Prediction Threshold Relative to Literature**
- FrugalGPT (LIT-001, LIT-006, LIT-013, LIT-019): 98% cost reduction vs. GPT-4.
- RouteLLM (LIT-003, LIT-008, LIT-016, LIT-020): 2x–5x cost reduction on MMLU / GSM8K.
- AutoMix (LIT-010): 50%+ cost reduction.
- RouterBench (LIT-015): 2–5x cost reduction.
- **HYP-006 asks for ≥15pp *incremental* reduction over a static router.** If the static router itself achieves ~40% cost reduction, then HYP-006 claims a bandit router hits ~55% — modest compared to literature. The hypothesis author frames this as an "absent question," implying it should be obvious to address.

### 3. **Single, Narrow Distribution Shift**
Experiment tests only MMLU → GSM8K (one topic shift). Real deployments experience diverse shifts: seasonal, linguistic, cohort, adversarial. A single shift provides weak evidence for generalization.

### 4. **Unrealistic Oracle Reward Signal**
Hypothesis assumes perfect correctness checking. In reality, ground truth is expensive (verifier model adds cost), noisy (user satisfaction ≠ correctness), and delayed (feedback lags). Using an oracle conflates the bandit algorithm's quality with reward signal quality.

### 5. **Mechanically Straightforward Experiment Design**
- Phase 1: Train logistic-regression router on MMLU embeddings. (Standard routing setup.)
- Phase 2: Run LinUCB online, measure cost delta. (Standard LinUCB recipe from textbooks.)
- Metric: cost reduction over final 100 queries. (Straightforward aggregation.)
No unexpected implementation challenges, no surprising design decisions.

### 6. **Low-Novelty Result Expectation**
If hypothesis passes: "Yes, a bandit router adapts to distribution shift and saves ~15pp additional cost vs. a static router." This is a straightforward confirmation of online-learning theory (bandits recover from distribution shift in O(√T) regret). It's not surprising.

### 7. **Ablation Complexity Not Pre-Specified**
If hypothesis passes, distinguishing LinUCB's contribution from "any online update helps" requires careful ablation (e.g., vs. simple moving-average re-tuning), which is not pre-registered.

## Recommendation

**Option A (Salvage)**: Increase the bar to ≥30pp incremental reduction; test on 3+ distribution shifts; include cost-of-adaptation overhead; add Thompson sampling and standard UCB baselines to isolate LinUCB advantage.

**Option B (Park)**: Focus on HYP-001–HYP-005, which exhibit more algorithmic novelty (distilled classifier, speculative cascade, multi-signal embedding, confidence cascade, Pareto-efficient 3-tier routing).
