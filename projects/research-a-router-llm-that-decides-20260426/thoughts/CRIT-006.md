---
{
  "id": "CRIT-006",
  "type": "Critique",
  "created_at": "2026-04-26T23:37:54+00:00",
  "parent_ids": [
    "HYP-004"
  ],
  "author": "critic",
  "summary": "HYP-004 applies a known entropy labeling mechanism to routing with under-specified conceptual link and generous success threshold",
  "body_path": "thoughts/CRIT-006.md",
  "target_id": "HYP-004",
  "mode": "boredom",
  "severity": "med"
}
---

HYP-004 proposes self-supervised routing via Haiku output entropy. While plausible, the hypothesis is built on an under-examined conceptual foundation and applies existing techniques with limited novelty.

## Conceptual Gap

The core assumption—that token-level entropy of model outputs predicts routing difficulty—is stated but not justified. Entropy measures uncertainty about correctness, not query complexity for routing decisions. Consider:

- A factual recall question (e.g., "What is the capital of France?") may have low entropy (Haiku is confident) and route correctly to Haiku.
- A creative writing prompt may have high entropy (many valid continuations) but be equally simple for all models, yet routes unnecessarily to Opus.
- A question requiring multi-step reasoning may have lower entropy if all samples fail identically, yet genuinely needs Opus.

Entropy is not difficulty; the hypothesis does not establish equivalence or correlation on the actual routing task.

## Novelty Concern

Kadavath et al. (2022) already demonstrated that entropy H(A|Q) discriminates correct from incorrect answers. HYP-004 adopts this verbatim as a labeling function for a router. This is engineering—applying a known signal to a new downstream task—rather than novel methodology. No cross-domain transplant is present.

## Technical Confounds

- **Semantic paraphrases (Kuhn et al. 2023)**: Raw token entropy is inflated by diverse paraphrases of the same meaning. On MMLU, this mis-labels easy-but-verbose questions as hard.
- **Model diversity (LIT-001)**: Larger models produce more diverse correct answers (HumanEval), causing entropy-based discrimination to weaken with scale. Haiku entropy may systematically conflate correctness diversity with difficulty.

These are acknowledged but not deeply investigated in the experiment design (k=5 sampling, length normalization).

## Success Threshold

A 5pp gap to supervised RouteLLM is forgiving. RouteLLM achieves >2x cost savings between two models with strong generalization. Matching within 5pp in ternary routing is plausible but uninspiring—not a compelling alternative to preference-data approaches.

## Cost Claim

HYP-004 claims to "eliminate costly human-labeled annotation" yet requires 5 Haiku calls per query. At 10k training queries, this is 50k calls—not free. FrugalGPT requires one-time labeling cost with no per-query overhead. The computational cost comparison is hand-waved.

## Verdict

Feasible but incremental. The core idea applies a known signal to a new task, with under-explored conceptual and technical gaps. Novelty would increase if the entropy → difficulty link were empirically grounded and confounds addressed head-on.

**Proposed fix**: Empirically validate entropy → difficulty link on MMLU/GSM8K (show entropy correlates with model error rate). Consider Semantic Entropy to reduce paraphrase issues. Lower success bar to ≤3pp if using token entropy, or raise to ≤7pp if using Semantic Entropy.
