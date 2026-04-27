---
{
  "id": "CRIT-012",
  "type": "Critique",
  "created_at": "2026-04-27T04:59:10+00:00",
  "parent_ids": [
    "HYP-004"
  ],
  "author": "critic",
  "summary": "HYP-004 is a narrow optimization of a well-understood technique; Platt scaling is standard calibration, and confidence-based routing is subordinate to stronger approaches",
  "body_path": "thoughts/CRIT-012.md",
  "target_id": "HYP-004",
  "mode": "boredom",
  "severity": "high",
  "proposed_fix": "Reframe as confidence-signal innovation (e.g., DINCO distractor normalization as pre-processing before Platt scaling) or drop in favor of multi-tier routing (HYP-005) which captures interaction structure between model pairs."
}
---

## HYP-004 Critique: Incremental Calibration Technique on Known-Weak Signal

HYP-004 proposes using Platt scaling to dynamically calibrate Haiku's verbalized confidence scores for cascade routing. The core contribution is replacing a fixed confidence threshold with a rolling window of 100-query-based dynamic re-calibration.

### Why This Is Boring

1. **Platt Scaling is 2011 Baseline Technology**: LIT-002 (On Calibration of Modern Neural Networks, 2016) already demonstrates that temperature/Platt scaling is the standard post-hoc calibration method. Applying it to LLM routing is mechanical, not inventive.

2. **Core Signal is Known to Be Broken**: LIT-007 (DINCO, ICLR 2026) demonstrates that LLMs exhibit *suggestibility bias* causing their verbalized confidence to saturate on incorrect answers. Platt scaling corrects for *miscalibration* (poor calibration curves), not for *systematically overconfident bias on hard examples*. The fundamental problem—that Haiku's confidence is unreliable—remains unfixed.

3. **Dynamic Thresholding Is Engineering, Not Science**: Updating thresholds every 100 queries is a parameter-tuning operation, not a novel mechanism. The space of threshold update strategies (fixed, rolling-window, exponentially-weighted, bandit-based) is well-explored in online learning. HYP-004 picks one without justification.

4. **Weak Target Metric**: A ≥20% cost reduction is modest relative to published baselines:
   - FrugalGPT (LIT-001, LIT-006): 98% cost reduction via cascade
   - RouteLLM (LIT-003, LIT-008): 2x cost savings on MMLU
   - EcoAssistant (LIT-012): surpasses GPT-4 by 10pp at <50% cost
   
   The 20% target suggests the method is expected to be weaker than existing approaches.

5. **No Novel Architecture or Approach**: HYP-004 combines two standard techniques (cascade routing + Platt scaling) on a standard signal (verbalized confidence). No new dataset, new metric, new model architecture, or new algorithmic principle.

6. **Superior Alternatives Unexplored**: 
   - LIT-026 (Self-Consistency): Majority vote over multiple samples is a more robust confidence proxy than single verbalized scores
   - LIT-028 (Conformal Language Modeling): Distribution-free coverage guarantees offer principled, theoretically grounded stopping rules—stronger than empirical threshold tuning
   - LIT-033 (Cross-Model Perplexity): Training-free routing signal that catches confident errors that classifiers miss

### Verdict

HYP-004 is an **incremental calibration engineering task**, not a research hypothesis. The work of applying Platt scaling to LLM confidence for routing is straightforward enough that it's likely already done in production systems. The boredom severity is **high** because:
- The mechanism is standard (Platt scaling)
- The signal is known-weak (verbalized confidence with suggestibility bias)
- The novelty is minimal (rolling-window threshold updates)
- Published baselines exceed the target gain by 5–50x

### Recommendation

Park HYP-004. If the team wants to pursue confidence-based routing, either:
1. **Reframe**: Use DINCO-style distractor normalization to fix the signal *before* applying Platt scaling (novel pre-processing), or
2. **Pivot**: Combine confidence with multi-model comparison (e.g., HYP-005's 3-tier routing structure) to capture interaction structure, not just individual calibration.
