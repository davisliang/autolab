---
{
  "id": "CRIT-013",
  "type": "Critique",
  "created_at": "2026-04-27T04:59:51+00:00",
  "parent_ids": [
    "HYP-006"
  ],
  "author": "critic",
  "summary": "HYP-006: low-novelty bandit transplant with unrealistic oracle assumptions; modest gains vs published baselines",
  "body_path": "thoughts/CRIT-013.md",
  "mode": "boredom",
  "severity": "high",
  "target_id": "HYP-006"
}
---

## Boredom Mode: HYP-006 is a Low-Novelty Transplant with Unrealistic Assumptions

**Core verdict**: HYP-006 applies off-the-shelf contextual bandits (LinUCB/Thompson sampling) to routing thresholds in a simulation with oracle labels. This is straightforward engineering with no novel algorithm, unrealistic deployment assumptions, and modest improvement targets.

### Why This Is Boring

1. **No algorithmic novelty**: Contextual bandits (Thompson sampling, LinUCB) are textbook algorithms from ~2010-2015. Applying them to routing thresholds is engineering, not research. No new algorithm, no new insight.

2. **Unrealistic oracle assumption**: Assumes per-query ground-truth labels for every deployed query. Production systems cannot afford this. The hypothesis sidesteps the real challenge—adapting with sparse, delayed, noisy feedback. This single assumption makes the work inapplicable.

3. **Modest improvement target**: ≥15% *incremental* cost reduction vs static router. Published offline routers already achieve 2-5x. A 15pp incremental gain is underwhelming; gains vanish if label quality degrades. No robustness analysis.

4. **Narrow evaluation**: Single distribution shift (MMLU→GSM8K), 500 queries (small for bandit convergence), entirely simulated, no real deployment signal. Generalization untested.

5. **Missing obvious baselines**: Periodic offline retraining, simple running-mean threshold adaptation, mixture-of-experts—no justification for why LinUCB + oracle outperforms these simpler alternatives.

### Proposed Fix

**Park this hypothesis.** Reformulate with:
- Realistic sparse/delayed reward signals
- Simple online retraining baseline comparison
- Multiple distribution shifts
- Label noise robustness analysis

Without these, deprioritize.
