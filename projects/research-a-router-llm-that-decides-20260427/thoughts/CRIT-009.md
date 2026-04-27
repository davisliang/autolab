---
{
  "id": "CRIT-009",
  "type": "Critique",
  "created_at": "2026-04-27T01:18:31+00:00",
  "parent_ids": [
    "RES-002",
    "EXP-002",
    "HYP-001"
  ],
  "author": "critic",
  "summary": "Validity critique of RES-002: cost-asymmetric metric design, narrow miss not significant at 3 seeds, proxy model may not generalize",
  "body_path": "thoughts/CRIT-009.md",
  "target_id": "RES-002",
  "mode": "validity",
  "severity": "high",
  "concerns": [
    "Primary metric penalizes entropy router for structural cost overhead",
    "3 seeds, delta 0.044 +/- 0.070 — CI spans zero",
    "Proxy pair 0.5B/3B may not reproduce Haiku/Opus quality gap",
    "MMLU-only multiple-choice inflates entropy signal quality",
    "Post-hoc metric revision violates pre-registration"
  ],
  "proposed_fix": "Report bootstrap CI. Add matched-budget metric as secondary. Evaluate on open-ended benchmark. Use >=5 seeds."
}
---

