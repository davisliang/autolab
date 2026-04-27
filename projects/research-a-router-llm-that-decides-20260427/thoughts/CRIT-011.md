---
{
  "id": "CRIT-011",
  "type": "Critique",
  "created_at": "2026-04-27T01:18:35+00:00",
  "parent_ids": [
    "RES-004",
    "EXP-004",
    "HYP-006"
  ],
  "author": "critic",
  "summary": "Validity critique of RES-004: d=384 LinTS needs 150k updates but gets 500 — cold-start is design flaw not finding; result not significant",
  "body_path": "thoughts/CRIT-011.md",
  "target_id": "RES-004",
  "mode": "validity",
  "severity": "high",
  "concerns": [
    "d=384 LinTS needs O(d^2) updates, 500 steps is 300x too few",
    "Simulated Beta oracle removes real LLM stochasticity",
    "5 seeds, stddev=0.068, CI spans zero — not significant",
    "Static baseline has structural warm-start advantage",
    "Cost penalty alpha=0.3 arbitrary with no sensitivity analysis"
  ],
  "proposed_fix": "Reduce context dim to d<=16. Warm-start TS from static router weights. Report convergence curves. Validate alpha sensitivity."
}
---

