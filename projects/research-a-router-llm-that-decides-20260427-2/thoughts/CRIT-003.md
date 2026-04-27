---
{
  "id": "CRIT-003",
  "type": "Critique",
  "created_at": "2026-04-27T01:57:14+00:00",
  "parent_ids": [
    "HYP-001"
  ],
  "author": "critic",
  "summary": "Multi-signal GBDT routing is incremental, uses standard tools, saturated problem space",
  "body_path": "thoughts/CRIT-003.md",
  "target_id": "HYP-001",
  "mode": "boredom",
  "severity": "med",
  "concerns": [
    "Incremental over single-signal baselines (RouteLLM, Hybrid LLM)",
    "No novel methodology: standard XGBoost application",
    "Straightforward NLP feature engineering with marginal novelty",
    "Problem space saturated (FrugalGPT, RouteLLM, AutoMix, RouterBench)",
    "No mechanistic insight identifying unique failure modes",
    "Proxy model setup weakens Haiku/Sonnet/Opus generalization"
  ],
  "proposed_fix": "Retire to parking lot; prioritize HYP-002 (confidence-cascade), HYP-003 (ensemble disagreement), HYP-005 (latency-aware), HYP-006 (bandits)"
}
---

## Boredom Critique: HYP-001 Multi-Signal GBDT Router

### Key Concerns

1. **Incremental over single-signal baselines**: RouteLLM (LIT-002, LIT-011) and Hybrid LLM (LIT-013) already demonstrate effective routing with embedding-only or threshold-based signals. Multi-signal fusion is the obvious next engineering step, not a conceptual leap.

2. **No novel methodology**: The proposal applies XGBoost, a standard off-the-shelf GBDT framework. There is no algorithmic innovation — just applying a well-understood tool to a new feature set. Industry ML uses this pattern routinely.

3. **Straightforward feature engineering**: Lexical diversity (type-token ratio), syntactic depth, perplexity under small LM — these are canonical NLP features taught in undergraduate courses. Combining them offers incremental, not fundamental, novelty.

4. **Heavily saturated problem space**: FrugalGPT, RouteLLM, Hybrid LLM, AutoMix, and RouterBench have comprehensively explored LLM routing trade-offs. The marginal gain (85% quality at 40% cost reduction) is not dramatically superior — Hybrid LLM already achieves 22–40% cost advantage with <1% quality drop (LIT-013), and FrugalGPT achieves 98% cost reduction via cascade (LIT-001).

5. **No mechanistic insight**: The hypothesis does not explain *why* multi-signal routing wins beyond invoking "nonlinear interactions." It identifies no unique failure mode of existing routers, nor proposes a new routing paradigm. Compare to HYP-002's mechanistically novel self-cascade paradigm or HYP-003's disagreement-based escalation.

6. **Experimental weaknesses**: Uses proxy models (Llama-3.2-1B/8B/70B) rather than the target models (Haiku/Sonnet/Opus), which may not generalize. No justification for why Llama proxy behavior reflects real model tier dynamics.

### Recommendation

**Retire to parking lot.** HYP-001 is a safe, incremental extension of RouteLLM/Hybrid LLM. The team should prioritize:
- **HYP-002**: Confidence-cascade paradigm (mechanistically novel)
- **HYP-003**: Ensemble disagreement (fresh mechanism from active learning)
- **HYP-005**: Latency-aware routing (addresses genuine gap ignored by prior work)
- **HYP-006**: Thompson Sampling bandits (online adaptation under distribution shift)

All four offer greater conceptual novelty and address gaps left by existing work.
