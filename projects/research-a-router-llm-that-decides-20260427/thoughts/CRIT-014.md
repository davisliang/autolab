---
{
  "id": "CRIT-014",
  "type": "Critique",
  "created_at": "2026-04-27T04:59:58+00:00",
  "parent_ids": [
    "HYP-008"
  ],
  "author": "critic",
  "summary": "Batch knapsack optimization is standard; conflates quality prediction (borrowed) with budget allocation (algorithmic); modest ≥20% target; unclear architectural distinction from HYP-004/HYP-006",
  "body_path": "thoughts/CRIT-014.md",
  "target_id": "HYP-008",
  "mode": "boredom",
  "severity": "medium"
}
---

Batch knapsack routing conflates two separable problems: quality estimation (borrows from existing routers) and budget allocation (standard algorithm). The ≥20% cost-reduction target is unambitious compared to published baselines (FrugalGPT 98%, RouteLLM 2x).

**Core concerns:**
1. **Standard algorithm, straightforward application**: Knapsack-style budget allocation is a well-established OR technique. Applying it to LLM routing is not novel unless paired with a novel quality-delta predictor—but HYP-008 does not propose one.
2. **Conflates layers**: Quality-delta prediction requires an existing quality estimator (not novel per HYP-008); knapsack optimization is algorithmic (standard). Unclear what the actual technical contribution is.
3. **Unclear distinction from HYP-004/HYP-006**: 
   - HYP-004: Platt-scaled dynamic thresholds
   - HYP-006: Online contextual-bandit adaptation
   - HYP-008: Batch-level budget allocation
   
   Is batch-level optimization a reparameterization of per-query threshold tuning (already explored)? Or a genuinely different architectural choice?
4. **Weak prediction target**: ≥20% cost reduction is unambitious compared to published work; threshold lacks justification.
5. **Aggregate-quality guarantee is problematic**: Allows individual query degradation; less useful in practice than per-query guarantees.
6. **Evaluation concern**: RouterBench is post-hoc on fixed data; optimization over a static benchmark does not prove the batch-framing is novel—just that you can optimize over a fixed dataset.

**Proposed fix**: Either (a) park as incremental, or (b) sharpen by proposing a specific novel component (e.g., a quality-delta predictor that beats embeddings) and then show batch allocation + your predictor outperforms per-query routing. Clarify architectural distance from HYP-004/HYP-006.
