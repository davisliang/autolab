---
{
  "id": "CRIT-004",
  "type": "Critique",
  "created_at": "2026-04-27T00:19:20+00:00",
  "parent_ids": [
    "HYP-004"
  ],
  "author": "critic",
  "summary": "HYP-004 applies established POMDP RL to routing; AutoMix prior art + modest novelty threshold → HIGH boredom risk",
  "body_path": "thoughts/CRIT-004.md",
  "mode": "boredom",
  "severity": "high",
  "target_id": "HYP-004"
}
---

# Critique: HYP-004 — Boredom Analysis

## Severity: HIGH

HYP-004 (RL-trained router with LLM-judge reward) is at high risk of boredom due to insufficient novelty and straightforward application of established techniques.

## Concerns

1. **Prior art directly addresses the problem**: AutoMix (LIT-011) already validates that sequential decision frameworks (POMDP-based RL) beat supervised routing. HYP-004 applies basic REINFORCE—a simpler RL algorithm—without novel algorithmic contribution.

2. **LLM-as-judge is well-established**: LIT-009 confirms LLM judges work at >80% human agreement. The reward formulation (quality_score - λ*cost) is a standard reward design; there is no novel insight here.

3. **Pareto frontier is expected by construction**: Training 5 policies at different λ values necessarily traces a Pareto frontier. Achieving dominance at ≥3 of 5 budget levels (60% threshold) is not a surprising outcome—it is the null hypothesis when RL converges properly.

4. **Novelty is engineering, not conceptual**: The main claimed innovations are:
   - 1M-param router (practical, not novel)
   - Fine-tuned DeBERTa judge (cost optimization, not algorithmic)
   
   These are optimizations, not conceptual breakthroughs worthy of a research paper.

5. **Incremental over AutoMix**: AutoMix already demonstrates RL routing works. This hypothesis does not advance the state-of-the-art in RL for routing; it is a straightforward application.

## Proposed Fix

**Deprioritize HYP-004 unless the experimental results reveal unexpected, non-obvious learned routing rules** that differ substantially from supervised routing intuition. For example, if the RL policy discovers that certain query types route to counterintuitive models (e.g., "short math → Sonnet not Haiku") *and* outperform supervised baselines by >15% at matched quality, then the mechanistic insight could justify inclusion.

Otherwise, **favor hypothesis space for**:
- **HYP-003** (speculative routing): CPU-transplant principle is conceptually novel
- **HYP-005** (consistency-based routing): Divergence-based signals are underexplored
- **HYP-006** (bandit routing): Online adaptation under distribution shift is timely

**Recommendation**: Park HYP-004 in ideas/parking_lot and revisit only if ablation experiments uncover non-obvious learned behavior.
