---
{
  "id": "CRIT-006",
  "type": "Critique",
  "created_at": "2026-04-27T00:19:45+00:00",
  "parent_ids": [
    "HYP-006"
  ],
  "author": "screen-boredom",
  "summary": "Thompson Sampling is predictable application of bandit literature; context encoding remains unspecified.",
  "body_path": "thoughts/CRIT-006.md",
  "target_id": "HYP-006",
  "mode": "boredom",
  "severity": "med",
  "concerns": [
    "Thompson Sampling for online LLM routing is a straightforward application of well-known bandit algorithms to an identified gap. Once distribution shift is recognized, Thompson Sampling is the obvious next step—the cross-domain transplant is shallow and predictable.",
    "Context encoding unspecified: relies on generic sentence-transformers despite routing needing query complexity, code/math semantics, and model-confusion signals.",
    "8pp AUC improvement lacks grounding: unclear if gain comes from Thompson Sampling superiority or any online adaptation on new distribution.",
    "No comparison to simpler online baselines (epsilon-greedy, moving-window outcome averaging)."
  ],
  "proposed_fix": "Strengthen novelty: (1) empirically compare Thompson Sampling vs simpler online baselines (epsilon-greedy, rolling window of LLM judge scores), OR (2) propose routing-informed context encoder combining syntax/semantic features, code patterns, and model-specific confusion signals rather than off-the-shelf embeddings."
}
---

