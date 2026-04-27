---
{
  "id": "CRIT-010",
  "type": "Critique",
  "created_at": "2026-04-27T04:59:03+00:00",
  "parent_ids": [],
  "author": "critic",
  "summary": "HYP-003 is near-duplicate of LIT-011 with metric mismatch: predicts routing accuracy instead of cost efficiency",
  "body_path": "thoughts/CRIT-010.md",
  "target_id": "HYP-003",
  "mode": "boredom",
  "severity": "high",
  "concerns": [
    "LIT-011 (Shnitzer et al. 2023) already solves sentence-embedding routing on MMLU with kNN and three sophisticated routing scores; HYP-003 adds k-means clustering + syntactic features — incremental feature engineering on solved problem",
    "Critical metric-target mismatch: HYP-003 predicts routing_accuracy_vs_oracle (classification agreement), but goal is cost efficiency. Oracle threshold (90% quality) is unvalidated and arbitrary; agreement with oracle ≠ cost savings",
    "Feature engineering is standard NLP practice: token count, vocabulary entropy, task-type prediction are well-known heuristics. Shnitzer et al. already achieved SOTA routing; syntactic elaboration is natural but not novel",
    "Unvalidated oracle design: cheapest model @ ≥90% Opus quality is heuristic. Why 90%? Different thresholds change oracle labels without changing actual utility. Ignores cost-suboptimal routing risk",
    "Limited experimental scope vs prior work: HYP-003 proposes MMLU held-out split with LR; LIT-011 used 29 datasets + explicit OOD analysis. No comparison to Shnitzer S_3 score or discussion of OOD failure modes"
  ],
  "proposed_fix": "Reframe to address cost efficiency, not accuracy: (1) Does oracle-matching accuracy predict cost gains? (2) Can syntactic features improve Shnitzer S_3 OOD generalization? (3) What oracle quality threshold minimizes cost? Or park and focus on true novelties: cross-domain transplants (HYP-002) or online learning (HYP-006)."
}
---

