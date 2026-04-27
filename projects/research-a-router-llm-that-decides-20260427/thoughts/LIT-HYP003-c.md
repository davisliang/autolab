---
{
  "type": "LitFinding",
  "arxiv_id": "2404.14618",
  "title": "Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing",
  "relevance": 0.88,
  "parent_ids": ["HYP-003"],
  "author": "literature-scout"
}
---

## Summary

Mallick et al. (2024, Microsoft) introduce a hybrid inference approach that routes queries between a small edge model and a large cloud model. A DeBERTa encoder is trained to predict the quality gap (BART score difference) between small and large model responses. Routing threshold is tunable at test time to trade quality for cost. Key finding: 40% fewer calls to the large model with no quality drop; probabilistic soft labels improve over hard binary labels by modelling response stochasticity.

## Key Claims

1. A DeBERTa-based router, trained with soft probabilistic labels (10 responses per query per model), is superior to hard-label routers.
2. Data transformation (shifting labels when large/small gap is extreme) improves routing when models differ greatly in quality.
3. "Easy" queries (small quality gap) can be reliably identified from input features alone, without seeing the response.
4. Cost advantage (% routed to small model) of 22-40% achievable at <1% quality drop.

## Relevance to HYP-003

This paper uses a single encoder model (DeBERTa) as feature extractor, rather than HYP-003's explicit multi-signal feature vector (embedding + syntax + task type). The Hybrid LLM approach implicitly learns all relevant features end-to-end from raw text, while HYP-003 proposes interpretable hand-crafted features combined with sentence embeddings via logistic regression. Comparison in performance between the two strategies (learned vs. engineered features) is an open question that HYP-003's ablation design can help answer.
