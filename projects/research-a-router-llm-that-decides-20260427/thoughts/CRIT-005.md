---
{
  "id": "CRIT-005",
  "type": "Critique",
  "created_at": "2026-04-27T00:19:21+00:00",
  "parent_ids": [],
  "author": "critic",
  "summary": "Boredom critique—consistency routing is incremental over known uncertainty signals; 3x Haiku cost for 4pp gain unclear",
  "body_path": "thoughts/CRIT-005.md",
  "target_id": "HYP-005",
  "mode": "boredom",
  "severity": "high"
}
---

---
id: CRIT-005
type: Critique
created_at: 2026-04-27T00:15:00+00:00
parent_ids: ["HYP-005"]
author: critic
summary: Boredom critique—consistency routing is incremental over known uncertainty signals; 3x Haiku cost for 4pp gain unclear
target_id: HYP-005
mode: boredom
severity: high
concerns: []
proposed_fix: null
body_path: thoughts/CRIT-005.md
---

## Boredom-Mode Critique: HYP-005

### Core concern
HYP-005 applies a **known and well-validated** uncertainty signal (multi-sample consistency/disagreement) to routing. The literature (LIT-016, LIT-019, LIT-023) already establishes that consistency across K samples is the best black-box failure-prediction signal. HYP-005 is a straightforward application of this known technique to the routing problem, not a novel mechanism or insight.

### Specific concerns

**1. No algorithmic innovation**
The mechanism is vanilla: sample K=3 times, measure pairwise divergence (BLEU or semantic similarity), threshold and route. This is a direct application of ensemble disagreement—a well-known uncertainty quantification method from 2015+ literature (deep ensembles, MC dropout, etc.). No learned weighting, no novel calibration, no mechanism transplant (unlike HYP-003's speculative routing or HYP-004's RL reward loop).

**2. Tripled routing latency, marginal gain prediction**
- Overhead: 3 Haiku calls vs 1 for entropy routing — 3x routing latency.
- Predicted improvement: 4pp on quality_at_budget_normalized.
- Cost-benefit analysis in the hypothesis is hand-wavy ("if 20% of queries would be sent unnecessarily").
- No empirical justification that multi-sample consistency on Haiku outweighs the latency tax.

**3. Contradicts own mechanism assumption**
The hypothesis assumes divergence catches "confidently wrong" failures that entropy misses. But:
- If a model is confidently *and consistently* wrong (all K samples agree on the same wrong answer), divergence is **low** (high consistency) → no escalation → failure undetected.
- This breaks the mechanism unless combined with entropy (reducing HYP-005 to a feature, not a standalone hypothesis).

**4. Subsumed by ensemble approaches**
The hypothesis concedes it is "orthogonal to HYP-001" and "can be combined." If combining entropy + divergence yields a better result, then the real hypothesis is HYP-001+HYP-005 ensemble, not HYP-005 alone. Running both wastes budget.

**5. Already explored in literature**
- LIT-018: "Showing LLMs many of their own samples before self-evaluation improves P(True)" — multi-sample context already validated.
- LIT-020: TruthfulQA flagged as the stress-test (LIT-020 explicitly names this dataset as adversarial).
- LIT-019: Consistency beats entropy at 0.605 vs 0.522 AUROC—but this is *failure prediction*, not *routing calibration*. Routing is a downstream task; gain may not transfer.

**6. Predicted gain is marginal and within noise**
4pp on a normalized metric with ≥3 seeds is vulnerable to:
- Variance across seeds and datasets.
- Possible failure of ablation (if the gain only materializes when combined with entropy, it doesn't survive the auto-ablation).
- Statistical power: uncertain whether 4pp is significant at the scale tested.

### Summary
HYP-005 is a competent, well-motivated *application* of known uncertainty signals to routing. But it lacks novelty (applies ensemble disagreement, a well-established method), has unclear cost-benefit (3x latency for 4pp marginal gain), and is likely subsumed by ensemble variants of HYP-001. It would be a reasonable *ablation* or *combination study* *after* HYP-001 passes, but as a standalone hypothesis competing for budget, it offers low scientific novelty and high execution risk (large prediction threshold relative to baseline gain).

### Recommendation
**Park HYP-005** and reserve it for a post-hoc ablation (if HYP-001 wins, test HYP-001+divergence as an ensemble). Do not prioritize as an independent experiment in this round.
