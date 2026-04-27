---
{
  "id": "CRIT-007",
  "type": "Critique",
  "created_at": "2026-04-27T00:20:03+00:00",
  "parent_ids": [
    "HYP-007"
  ],
  "author": "critic",
  "summary": "HYP-007: decompose-then-route is straightforward composition with scoped empirical value and overhead risks",
  "body_path": "thoughts/CRIT-007.md",
  "target_id": "HYP-007",
  "mode": "boredom",
  "severity": "medium",
  "concerns": [
    "Query decomposition (Least-to-Most, DSP, DecomP) and LLM routing (RouteLLM, FrugalGPT) are established; proposed mechanism simply applies existing routing to sub-questions—no novel routing algorithm or decomposition strategy.",
    "Scope tightly limited to HotpotQA (2-hop by design); unclear generalization to other query types.",
    "Hypothesis explicitly acknowledges decomposition overhead as a risk; with N=2 sub-questions, overhead could negate savings. No principled analysis of when decomposition is worthwhile.",
    "Merging strategy is simplistic (concatenate + synthesize). No discussion of handling conflicting or incomplete sub-answers.",
    "Contribution to routing research is incremental: applying routing at finer granularity is a natural engineering idea, not a research insight."
  ],
  "proposed_fix": "Strengthen by: (1) proposing a principled, generalizable decomposition strategy beyond Haiku few-shot, (2) analyzing the granularity-cost tradeoff systematically, or (3) targeting a domain where decomposition quality is the bottleneck (open-domain QA). If proceeding with HotpotQA, include overhead-sensitivity ablations."
}
---

