---
{
  "id": "CRIT-HYP-005",
  "type": "Critique",
  "created_at": "2026-04-27T06:15:00+00:00",
  "parent_ids": ["HYP-005"],
  "author": "critic",
  "summary": "HYP-005 is a standard model-selection ablation with a foreordained outcome: tautological that 3-tier > 2-tier at some cost point; no novel insight or technique.",
  "body_path": "thoughts/CRIT-HYP-005-BOREDOM.md",
  "target_id": "HYP-005",
  "mode": "boredom",
  "severity": "high",
  "concerns": [
    "Tautological outcome: Adding a middle tier with a reasonable cost ratio (Sonnet=5x vs Haiku=1x/Opus=15x) will almost certainly improve the Pareto frontier at some operating point. The hypothesis is asking 'do more choices help?' The answer is yes by definition unless the middle tier is strictly dominated, which is unlikely given Anthropic's model lineup.",
    "Standard classifier architecture selection: The core experiment is 2-class vs 3-class logistic regression on embeddings. This is textbook model selection, not a novel routing strategy. All of HYP-001–HYP-004 already assume 3-tier is better; HYP-005 is just empirically validating an assumption the project team already made.",
    "Limited scope and generalization: The finding is specific to MMLU 1k-query subset and Anthropic's exact cost ratios (1x/5x/15x). It won't inform design choices for (a) other benchmarks, (b) other model families, (c) other cost regimes. RouterBench already covers 11 models and 8 datasets without isolating intermediate-tier value, suggesting the community doesn't find this distinction critical.",
    "No methodological novelty: The experiment design (oracle labels, Pareto sweep, logistic regression baseline) is standard from the routing literature. The ≥3pp threshold is arbitrary and not grounded in practical deployment cost-quality tradeoffs.",
    "Derivative of prior work: Every routing paper (FrugalGPT, RouteLLM, HybridLLM, RouterBench, AutoMix) studies routing across models of different capacities. The fact that hierarchical cascades exist (EcoAssistant, FrugalGPT) is already evidence that intermediate tiers have value. This hypothesis adds no new evidence beyond 'intermediate tiers help on MMLU.'",
    "Risk of parking the entire project: If HYP-005 fails (3-tier does not beat 2-tier by ≥3pp), the project premise collapses because HYP-001–HYP-004 are all 3-tier-dependent. But if HYP-005 passes (trivially likely), it only confirms the team's original design assumption—no actionable insight."
  ],
  "proposed_fix": "Reframe HYP-005 as a meta-question: 'What is the maximum realizable Sonnet-only zone (queries Haiku fails, Sonnet succeeds, Opus unnecessary)?' and measure not just 3-tier > 2-tier accuracy, but *how much classification error can we tolerate before the middle tier stops paying for itself?* This would produce a threshold sensitivity analysis: 'Sonnet is worth including if we can achieve >X% routing accuracy to Sonnet-correct queries.' That is actionable across model families and cost regimes."
}
---

## Boredom Critique: HYP-005

### Summary

HYP-005 asks whether a 3-tier router Pareto-dominates a 2-tier router on MMLU by ≥3pp accuracy gain at matched cost. This is a **tautological model-selection question** with a foreordained positive outcome: adding a middle tier with a sensible cost ratio will almost certainly improve some operating point of the Pareto frontier, unless the tier is strictly dominated (unlikely). The hypothesis validates an assumption the project team already made (all prior hypotheses assume 3-tier is beneficial) but offers no novel insight, methodology, or learning.

### Core Issues

1. **Tautology**: If Sonnet is cheaper than Opus but more capable than Haiku, there *must* exist a query subset where Sonnet is the cost-optimal answer. Adding it strictly weakly improves the Pareto frontier. The only question is magnitude (≥3pp), which is empirically measurable but not interesting—it's a given that more options help unless the middle tier is dominated.

2. **Already assumed**: The hypothesis explicitly acknowledges that HYP-001–HYP-004 all assume 3-tier is better. HYP-005 is just confirming the team's prior design choice, not testing a genuinely open question.

3. **No novelty**: The experiment (oracle labels, logistic regression classifier, Pareto sweep) applies standard techniques from the routing literature. RouterBench already demonstrates that routing across 11 models on 8 datasets is beneficial; singling out the 2-tier vs 3-tier comparison adds no methodological contribution.

4. **Scope too narrow**: The result is specific to MMLU, Anthropic's cost ratios, and a 1k-query subset. It won't generalize to other benchmarks, other model families, or other cost regimes where the relative value of intermediate tiers may differ.

5. **Risk structure is inverted**: If HYP-005 passes (expected), it's just confirmation. If it fails (unlikely), the entire project collapses because HYP-001–HYP-004 all depend on 3-tier being better. There's no scenario where HYP-005 produces an actionable insight beyond "yes, intermediate tiers help."

### Proposed Fix

Reframe HYP-005 as a **sensitivity analysis**:

- **New hypothesis**: "A 3-tier router is cost-optimal only if the routing classifier achieves >X% accuracy on Sonnet-sufficient queries (false-positive rate on Sonnet calls <Y%). Beyond that threshold, classification error erodes the middle tier's value."
- **Metric**: Maximum tolerable classification error (per-class precision/recall thresholds) such that Sonnet calls remain cost-justified.
- **Outcome**: Produces a **deployment guideline** applicable across model families: 'Include a middle tier if you can achieve >X% precision on medium-confidence queries.' That generalizes.

This shifts from "does 3-tier help on MMLU?" (yes, obviously) to "under what conditions does the middle tier pay for itself?" (interesting across domains).

