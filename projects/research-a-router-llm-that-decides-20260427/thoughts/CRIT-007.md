---
{
  "id": "CRIT-007",
  "type": "Critique",
  "created_at": "2026-04-27T04:44:13+00:00",
  "parent_ids": [
    "RES-001",
    "EXP-001",
    "HYP-002"
  ],
  "author": "critic",
  "summary": "RES-001 validity critique: simulation-only design, trivial sanity gate, and assumed judge ROC limit generalizability of negative result",
  "body_path": "thoughts/CRIT-007.md",
  "target_id": "RES-001",
  "mode": "validity",
  "severity": "med",
  "concerns": [
    "Pure simulation — no real LLM API calls; parametric accuracy curves may not reflect real task structure",
    "Sanity gate trivially passed: deterministic 30/70 label mix guarantees loss drop",
    "Judge TPR/FPR are free parameters on assumed ROC shape, not derived from a trained judge",
    "Only 3 seeds — meets minimum but wide CI on delta",
    "Cost ratio fixed at 1:5; no sensitivity analysis",
    "No latency analysis despite HYP-002 flagging it as open question"
  ],
  "proposed_fix": "Negative result is directionally trustworthy (structural overhead argument is sound). Strengthen with: (1) real API calls on 100-question GSM8K subset, (2) cost-ratio sensitivity sweep (1:3 to 1:10) to find break-even, (3) 10+ seeds for tighter CI."
}
---

## Validity Critique: RES-001

### Overall assessment

RES-001 reports a clear negative result: the speculative cascade saves 13.2pp vs always-Sonnet while the input-feature baseline saves 18.9pp, yielding a -5.72pp delta against the +8pp threshold. The direction is credible — the structural overhead argument (always paying Haiku+judge even on escalated queries) is mathematically sound. However, several design choices limit how strongly this negative result generalizes.

### Concern 1: Pure simulation, no real LLM calls (severity: high)

The entire experiment runs in numpy. Difficulties are drawn from Beta(2,3); model correctness uses sigmoid curves with hardcoded thresholds (0.35 for Haiku, 0.60 for Sonnet). Real LLM behavior on GSM8K exhibits non-monotonic difficulty patterns, partial credit scenarios, and format-dependent failures that a smooth sigmoid cannot capture. The simulation assumes independence of model outcomes conditional on difficulty, which is unlikely for models sharing similar training data.

**Impact**: The negative result rests on the structural cost argument (escalation overhead dominates information advantage), which holds regardless of the accuracy model. But the *magnitude* (-5.72pp) is simulation-dependent and should not be cited as a precise estimate.

### Concern 2: Sanity gate is trivially passed (severity: med)

The sanity gate (run.py:181-206) generates random predictions, then computes `trained_preds = 0.3 * random + 0.7 * labels + noise`. This deterministically produces a large loss drop (~80%) regardless of the underlying problem. It does not validate that any component actually learns or functions correctly.

**Impact**: The sanity gate provides no meaningful validation. It should have tested that the judge or router achieves non-trivial discrimination on held-out examples.

### Concern 3: Assumed judge ROC curve (severity: med)

The speculative cascade sweeps judge TPR from 0.60 to 0.95 with FPR linearly correlated as `fpr = 0.02 + 0.13*(tpr-0.60)/0.35` (run.py:132). This assumes a specific ROC shape. A real judge (regex + CoT length heuristic per HYP-002) might achieve TPR > 0.85 at FPR < 0.05, potentially making the cascade competitive. The negative result is conditional on assumed judge quality.

### Concern 4: Limited statistical power (severity: low)

Three seeds yield mean delta -5.72 ± 1.64. The approximate 95% CI is [-9.42, -2.02] — excludes zero and the +8pp threshold, but the true disadvantage magnitude is imprecise. For a simulation this cheap to run, 10+ seeds would tighten the estimate substantially.

### Concern 5: Fixed cost ratio (severity: low)

The 1:5 Haiku:Sonnet cost ratio is hardcoded. At 1:10, escalation premium (11.2 vs 10.0) is proportionally smaller, potentially favoring the cascade. No sensitivity analysis was performed.

### Concern 6: Missing latency dimension (severity: low)

HYP-002 explicitly flags latency as an open question. The experiment measures only cost. Serial Haiku→judge→Sonnet adds latency that could independently argue for or against the approach.

### Baseline parity

The baseline is well-designed: same model outcomes, same difficulty draws per seed, matched quality tolerance (2pp). The input-feature router uses reasonable noise (σ=0.10) and threshold sweep. No concerns about baseline fairness.

### Statistical note

The `config` argument to `run_full` is unused in the comparison logic — both proposed and baseline are computed every call regardless. Not a bug, but misleading interface.

### Summary

The negative result (-5.72pp vs +8pp threshold) is directionally sound: structural overhead of always-running-Haiku-plus-judge dominates the output-quality information advantage. However, simulation-only design, trivial sanity gate, and assumed judge ROC mean the precise magnitude is unreliable. Sufficient to fail HYP-002 under protocol. A real-API validation on 100 GSM8K questions + cost-ratio sensitivity analysis would strengthen the conclusion and clarify break-even conditions.
