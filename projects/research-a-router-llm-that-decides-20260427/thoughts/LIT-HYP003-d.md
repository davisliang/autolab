---
{
  "type": "LitFinding",
  "arxiv_id": "2403.12031",
  "title": "RouterBench: A Benchmark for Multi-LLM Routing System",
  "relevance": 0.78,
  "parent_ids": ["HYP-003"],
  "author": "literature-scout"
}
---

## Summary

Bieker et al. (2024) introduce RouterBench: a comprehensive evaluation framework for LLM routing with over 405k pre-generated inference outcomes from 11 models across 8 datasets. They propose a cost-quality tradeoff metric and evaluate both predictive (no inference needed at route time) and non-predictive (cascading) routers. Predictive routing via trained classifiers on input embeddings consistently outperforms single-model strategies at matched cost.

## Key Claims

1. Routing can reduce API costs by 2-5× at comparable quality levels (empirically validated across diverse tasks).
2. Simple predictive routers (classifiers on embeddings) outperform heuristic baselines and single models.
3. Standardized benchmark reveals that some routers don't generalise to complex tasks or newer models.
4. RouterBench enables zero-inference evaluation of new routing strategies—important for reproducibility.

## Relevance to HYP-003

RouterBench validates the premise of HYP-003 (lightweight classifiers can achieve substantial routing gain) and provides an evaluation methodology (cost-quality curve) that complements oracle accuracy. Notably, the benchmark includes MMLU data with multi-model outcomes, which is precisely the target dataset for HYP-003. The 2-5× cost reduction finding sets a practical upper bound for what the multi-signal LR router should aim for.
