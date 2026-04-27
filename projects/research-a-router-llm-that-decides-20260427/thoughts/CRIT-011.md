---
{
  "id": "CRIT-011",
  "type": "Critique",
  "created_at": "2026-04-27T04:59:08+00:00",
  "parent_ids": [
    "HYP-002"
  ],
  "author": "critic",
  "summary": "Output-conditioned routing already explored; judge too simplistic; cost asymmetry breaks transplant",
  "body_path": "thoughts/CRIT-011.md",
  "target_id": "HYP-002",
  "mode": "boredom",
  "severity": "med",
  "concerns": [
    "LIT-022 (LLM-Blender) already validates output-conditioned routing premise. HYP-002 is primarily cheap-judge engineering optimization, not novel mechanism.",
    "Regex judge (answer extraction + CoT length) weak signal—barely distinguishes from input-feature routing. Strong judge required for observe actual output quality premise; this design undermines it.",
    "Speculative decoding transplant analogy superficial: token-level speculation works because draft is batched, nearly free. At model level, Haiku costs money on every query; escalation overhead 24% (6.2 vs 5.0). Asymmetry should surface in design, not experiment.",
    "Narrow testbed (GSM8K math with 40% easy problems). Skewed difficulty distribution unlikely to generalize to balanced datasets (MMLU). LIT-020 shows RouteLLM already 2x cost reduction on GSM8K.",
    "Empirical failure -5.72pp is symptomatic: cheap model + judge + expensive escalation is economically dominated. No ablation path forward (judge cannot be cheaper; escalation cost fixed)."
  ],
  "proposed_fix": "Park HYP-002. If output-conditioned routing pursued: (a) train much stronger learned judge on quality labels, or (b) two-stage: input features pre-filter to high-uncertainty queries, then judge escalates only those. Current design simultaneously too simple (judge) and too expensive (always-run Haiku)."
}
---

