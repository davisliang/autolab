---
{
  "id": "CRIT-001",
  "type": "Critique",
  "created_at": "2026-04-26T00:00:00+00:00",
  "parent_ids": ["HYP-004"],
  "author": "critic",
  "summary": "HYP-004 is incremental; combines established techniques with conservative 20% target far below published baselines",
  "target_id": "HYP-004",
  "mode": "boredom",
  "severity": "high",
  "body_path": "thoughts/CRIT-HYP004-BOREDOM.md"
}
---

## Boredom Critique: HYP-004

### Core Concern: Incremental Combination of Established Techniques

HYP-004 proposes confidence-cascade routing with Platt-scaled dynamic thresholds. However, each component is well-established:

1. **Platt Scaling**: Foundational calibration technique from 2000; LIT-002 confirms it is the "most effective post-hoc confidence calibration method" in neural networks.
2. **Confidence-Based Routing**: Extensively explored in RouteLLM, FrugalGPT, and other cascade papers (LIT-001, LIT-003, LIT-008, LIT-016).
3. **Dynamic Thresholding**: Updating thresholds online is a standard engineering practice; not a research contribution.

The proposed novelty—moving from *fixed* to *dynamic* thresholds updated every 100 queries—is **engineering**, not research. This is an incremental optimization within a well-trodden design space.

### Conservative Target Relative to Published Baselines

- **HYP-004 target**: ≥20% cost reduction
- **Published baselines**: 
  - FrugalGPT (LIT-001, LIT-006): 98% cost reduction
  - RouteLLM (LIT-003, LIT-008, LIT-016): 2x (100%) cost reduction
  - EcoAssistant (LIT-012): Surpasses GPT-4 at <50% cost

Proposing 20% improvement in a space where published systems achieve 2–100x is unambitious. The hypothesis does not articulate why dynamic Platt scaling would substantially outperform what FrugalGPT and RouteLLM already deliver.

### Unresolved Blocker: Signal Quality

HYP-004 explicitly lists as an open question: "Is Haiku's self-reported confidence well-calibrated enough to be useful?" 

This is a critical risk:
- LIT-007 (DINCO) shows that verbalized LLM confidence is **overconfident** and requires distractor normalization to improve calibration.
- No evidence in HYP-004 that Haiku's 1–10 prompt-elicited confidence will be reliable enough to drive a cascade decision.

Without a prior ablation confirming the confidence signal is usable, this experiment risks measuring the failure of a weak signal rather than the success of dynamic thresholding.

### Recommendation

**Park HYP-004** until either:
1. A prior ablation confirms Haiku's self-reported confidence is calibrated well enough to be predictive of correctness on MMLU/GSM8K, or
2. The hypothesis is reframed to focus on a genuinely novel component (e.g., learning confidence calibration end-to-end via preference data, or a domain-adaptive routing mechanism).

As stated, HYP-004 is a straightforward engineering application of published techniques with a conservative target and an unvalidated critical assumption.
