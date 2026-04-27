---
{
  "id": "CRIT-004",
  "type": "Critique",
  "created_at": "2026-04-26T23:37:18+00:00",
  "parent_ids": [
    "HYP-001"
  ],
  "author": "critic",
  "summary": "HYP-001 is redundant with Hybrid LLM; no novel mechanism or feature signal",
  "body_path": "thoughts/CRIT-004.md",
  "target_id": "HYP-001",
  "mode": "boredom",
  "severity": "high",
  "concerns": [
    "LIT-019 (Hybrid LLM) is architecturally identical—both use a learned classifier to route to Haiku/Sonnet/Opus tiers. The only difference is the feature set (parse depth + TTR), which is marginal engineering, not novelty.",
    "Hand-crafted features are a dead-end. LIT-008/LIT-009 (RouteLLM) uses learned BERT embeddings and achieves >2x cost savings with strong OOD generalization.",
    "Achieves 85% routing accuracy, but Hybrid LLM already gets 40% fewer large-model calls with <1% quality loss (LIT-007/LIT-019). Not a meaningful improvement.",
    "No online adaptation, self-supervised learning, or novel mechanism. Unlike HYP-003 (BOLA), HYP-004 (entropy), HYP-005 (latency-aware), this is purely offline supervised classification—the frontier moved past this.",
    "RouterBench (LIT-021) shows simple classifiers are already competitive. Building another supervised classifier adds no novelty."
  ],
  "proposed_fix": "Park HYP-001 and focus on mechanistically novel hypotheses: online adaptation (HYP-003), self-supervised learning (HYP-004), latency/SLA awareness (HYP-005), conversation context (HYP-006)."
}
---

## Boredom Critique: HYP-001

HYP-001 proposes a supervised ternary classifier using hand-crafted features (token count, TTR, parse depth, task type) to route queries. **This is not novel and does not advance the frontier.**

### Core Redundancy
LIT-019 (Hybrid LLM) already does this—a learned classifier routing to different tiers with 40% fewer large-model calls at <1% quality loss. HYP-001 merely swaps feature sets and claims novelty. The architecture is identical.

### Hand-crafted Features Are Obsolete
- RouteLLM (LIT-008, LIT-009) learned embeddings from preference data, achieving >2x cost savings with strong OOD generalization.
- Hand-crafted lexical/syntactic features cannot compete with learned representations.
- Syntax trees and type-token ratios are weak proxies for query complexity; learned embeddings capture semantic structure.

### Existing Baselines Already Win
- Hybrid LLM: 40% fewer calls at <1% quality loss.
- FrugalGPT: 98% cost reduction via generation scoring.
- RouteLLM: >2x cost savings with strong OOD generalization.
- RouterBench: simple classifiers are already saturated.

HYP-001 predicts "85% routing accuracy"—a meaningless metric relative to these results. Routing accuracy != cost efficiency or user quality.

### Missing Novelty Vectors
The other hypotheses have genuine novelty:
- **HYP-003**: BOLA-inspired **online adaptation** (cross-domain transplant).
- **HYP-004**: **Self-supervised entropy labeling** (eliminates annotation cost).
- **HYP-005**: **Latency-SLA-aware routing** (new optimization objective).
- **HYP-006**: **Conversation-aware routing** (temporal structure).

HYP-001 has none of these. It is purely offline supervised classification—a solved problem for 3+ years.

### Recommendation
**Recommend severity=high parking.** HYP-001 is a surface-level engineering variation on prior work, not a research contribution.
