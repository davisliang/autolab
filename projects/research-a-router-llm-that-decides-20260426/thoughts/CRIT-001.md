---
{
  "id": "CRIT-001",
  "type": "Critique",
  "created_at": "2026-04-26T23:50:00+00:00",
  "parent_ids": ["HYP-004"],
  "author": "critic",
  "summary": "HYP-004 applies a known entropy labeling mechanism (Kadavath et al. 2022) to routing with an under-specified conceptual link and a generous success threshold, reducing novelty.",
  "body_path": "thoughts/CRIT-001.md",
  "target_id": "HYP-004",
  "mode": "boredom",
  "severity": "med",
  "concerns": [
    "Conceptual gap not addressed: Entropy measures model *correctness uncertainty*, not *routing difficulty*. A query could be hard to answer correctly but trivial to route, or easy to answer but have high output diversity. HYP-004 assumes entropy → difficulty without establishing this linkage.",
    "Limited novelty: The core mechanism—using entropy as a labeling function—is directly from Kadavath et al. (2022). Applying it to routing training is a straightforward engineering extension, not a novel algorithmic contribution.",
    "Known confounds under-investigated: Semantic paraphrases inflate entropy (Kuhn et al. 2023), and larger model size increases diversity of correct answers (LIT-001), both acknowledged but not deeply probed in HYP-004's design.",
    "Generous success threshold: 5pp margin to supervised RouteLLM is forgiving. RouteLLM achieves >2x cost savings with strong generalization; matching within 5pp is an incremental claim, not a breakthrough.",
    "Bootstrapping efficiency claim unsubstantiated: HYP-004 claims to \"eliminate costly human-labeled annotation\" yet requires 5k Haiku samples at inference time per labeling run. FrugalGPT requires labeled data but no per-query sampling overhead. Cost comparison is not clearly in favor of entropy labeling."
  ],
  "proposed_fix": "Sharpen conceptual claim by empirically validating the entropy → difficulty link on MMLU/GSM8K (e.g., show entropy correlates with model error rate, not just Haiku correctness). Consider Semantic Entropy (Kuhn et al.) as the labeling mechanism to reduce paraphrase-induced false positives. Lower success bar to ≤3pp if retaining token entropy, or raise it to ≤7pp if using Semantic Entropy to reflect added labeling cost."
}
---

## Boredom Assessment

HYP-004 proposes self-supervised routing via Haiku output entropy. While plausible, the hypothesis is built on an under-examined conceptual foundation and applies existing techniques with limited novelty.

### Conceptual Gap

The core assumption—that token-level entropy of model outputs predicts routing difficulty—is stated but not justified. Entropy measures *uncertainty about correctness*, not *query complexity for routing decisions*. Consider:

- A factual recall question (e.g., "What is the capital of France?") may have low entropy (Haiku is confident) and route to Haiku, correctly.
- A creative writing prompt may have high entropy (many valid continuations) but be equally simple for all models to attempt, yet routes to Opus unnecessarily.
- A question requiring multi-step reasoning may have lower entropy if all samples fail identically, yet genuinely needs Opus.

Entropy is not difficulty; the paper does not establish equivalence or even correlation on the actual routing task.

### Novelty Concern

Kadavath et al. (2022) already demonstrated that entropy H(A|Q) discriminates correct from incorrect answers across multiple tasks. HYP-004 adopts this verbatim as a labeling function for a router. This is engineering—applying a known signal to a new downstream task—rather than a methodological or algorithmic innovation. The cross-domain transplant angle is absent; it is a direct application.

### Technical Confounds

- **Semantic paraphrases (Kuhn et al. 2023)**: Raw token entropy is inflated by diverse paraphrases of the same meaning. On MMLU factual tasks, this will mis-label easy-but-verbose questions as hard.
- **Model diversity (LIT-001)**: Larger models produce more diverse *correct* answers (e.g., on HumanEval), causing AUROC to *decrease* with scale. Haiku entropy may systematically conflate correctness diversity with difficulty, biasing the labeler.

These are known and acknowledged in HYP-004, but the experiment design (k=5 sampling, length normalization) does not deeply investigate whether these confounds dominate in a routing context.

### Success Threshold

A 5pp gap to supervised RouteLLM is forgiving. RouteLLM routes between two models with >2x cost savings, and even binary routers on diverse benchmarks achieve <3pp degradation with standard approaches. Matching within 5pp in the ternary case is plausible but uninspiring—it does not establish that self-supervised routing is a compelling alternative to cheap preference-data collection.

### Cost Claim

The abstract motivation claims to "eliminate costly human-labeled annotation," but HYP-004 requires 5 Haiku calls per query to generate entropy labels. At scale (10k training queries), this is 50k calls—not free. FrugalGPT trades a one-time labeling cost (human or synthetic) for no per-query overhead. The computational cost comparison is hand-waved.

### Verdict

HYP-004 is feasible and the 5pp hypothesis is likely achievable, but the core idea is an incremental application of an existing signal to a new task, with under-explored conceptual and technical gaps. If the entropy → difficulty link were empirically grounded and the confounds were addressed head-on, novelty would increase.
