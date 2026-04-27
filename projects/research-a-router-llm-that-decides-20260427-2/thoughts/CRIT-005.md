---
{
  "id": "CRIT-005",
  "type": "Critique",
  "created_at": "2026-04-27T01:57:22+00:00",
  "parent_ids": [
    "HYP-003"
  ],
  "author": "critic",
  "summary": "[Boredom] Ensemble disagreement is an old, well-validated technique; modest novelty over Plex baseline",
  "body_path": "thoughts/CRIT-005.md",
  "target_id": "HYP-003",
  "mode": "boredom",
  "severity": "medium"
}
---

## Critique CRIT-003: Ensemble Disagreement Lacks Novelty

### Boredom Summary
HYP-003 transplants the well-established ensemble-disagreement uncertainty heuristic from active learning into LLM routing without sufficient methodological novelty or improvement over existing uncertainty-based escalation (LIT-016 Plex). The target 20% reduction is modest and already matched by prior work.

### Key Concerns

1. **Weak Novelty**: The mechanism (Query by Committee disagreement) is a 30-year-old technique. While applying it to routing is new, the intellectual content is thin — it's a domain transplant without adaptation.

2. **Competitive Baseline Already Exists**: Plex (LIT-016) already shows that uncertainty-guided selective prediction yields 20–40% improvements at scale. HYP-003 targets exactly 20% — the lower bound of the existing literature. The paper will struggle to argue "this is novel" when Plex already does it.

3. **Unclarified Computational Overhead**: Running 5 routing classifiers (vs 1) means 5× forward passes. The hypothesis does not budget for this cost. If each forward pass costs 10ms, that's 50ms per query — potentially negating the token-cost savings in latency-constrained settings.

4. **Hard-Query Definition is Leaky**: Defining "hard queries" as those where small_quality < 0.7 × large_quality conflates two things:
   - What the routing decision should predict (query difficulty)
   - What actually happens post-inference (small model actually fails)
   
   If hard-query labels are derived from the test set, the metric is tautological.

5. **Weak Baseline Comparison**: Comparing against a single MLP classifier is not enough. Need to compare against:
   - Simple uncertainty from a single classifier's output logits
   - Simpler difficulty-based heuristics
   - Does the committee genuinely improve over a single well-trained classifier with temperature scaling?

6. **Modest Improvement Target**: 20% relative reduction is the lower bound of what Plex already achieved. Not sufficient to claim a contribution if Plex already does it.

### Proposed Fix
- **Option A** (Reject/Park): If the goal is ensemble disagreement validation, run HYP-003 as an **ablation** of HYP-002 (confidence cascade), isolating committee-vs-single in the presence of self-assessment.
- **Option B** (Strengthen): Add adaptive calibration (e.g., Platt scaling per query difficulty bin). Make it a methodological contribution beyond the transplant.
