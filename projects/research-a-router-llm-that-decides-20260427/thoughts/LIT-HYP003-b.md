---
{
  "type": "LitFinding",
  "arxiv_id": "2305.05176",
  "title": "FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance",
  "relevance": 0.82,
  "parent_ids": ["HYP-003"],
  "author": "literature-scout"
}
---

## Summary

Chen, Zaharia & Zou (2023) propose FrugalGPT, a framework for cost-aware LLM usage via three strategies: prompt adaptation, LLM approximation, and LLM cascade. The cascade component is most relevant: it sequences queries through increasingly expensive LLMs and stops when a DistilBERT-based scoring function certifies sufficient quality. FrugalGPT achieves up to 98% cost reduction vs GPT-4 at matched accuracy on HEADLINES/OVERRULING/CoQA.

## Key Claims

1. LLM APIs vary by 2 orders of magnitude in cost; adaptive cascade reduces median spend dramatically.
2. A DistilBERT regression scoring function, trained on (query, answer) pairs to predict correctness, is effective despite being tiny compared to the LLMs it gates.
3. Learned per-query routing is substantially better than always routing to the cheapest or most expensive model.
4. LLM cascade outperforms single-model approaches even at matched cost budgets.

## Relevance to HYP-003

Establishes the feasibility of lightweight learned scoring models (DistilBERT-scale) for LLM routing. FrugalGPT uses query+answer features; HYP-003 proposes a query-only signal (no generation cost at routing time). FrugalGPT is a strong baseline for cost-quality tradeoff but does not directly target oracle routing accuracy as HYP-003 does.
