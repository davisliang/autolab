---
{
  "id": "CRIT-010",
  "type": "Critique",
  "created_at": "2026-04-27T01:18:33+00:00",
  "parent_ids": [
    "RES-003",
    "EXP-003",
    "HYP-007"
  ],
  "author": "critic",
  "summary": "Validity critique of RES-003: weak merger is dominant failure mode, always-Opus baseline trivially conservative, strict F1 tolerance hides Pareto value",
  "body_path": "thoughts/CRIT-010.md",
  "target_id": "RES-003",
  "mode": "validity",
  "severity": "med",
  "concerns": [
    "0.5B merger 12% failure rate drives 3.7pp gap",
    "Always-Opus baseline has no routing intelligence",
    "Simulated cost model unvalidated against real pricing",
    "1pp F1 tolerance too strict for 69% cost reduction",
    "HotpotQA 2-hop only — no generalization claim possible"
  ],
  "proposed_fix": "Repeat with sonnet-tier merger. Add whole-query-routed baseline. Report Pareto frontier at multiple tolerance bands."
}
---

