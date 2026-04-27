---
id: LIT-HYP002-d
type: LitFinding
arxiv_id: "2406.18665"
title: "RouteLLM: Learning to Route LLMs with Preference Data"
relevance: 0.88
parent_ids: ["HYP-002"]
author: literature-scout
summary: "Strongest input-feature router (2024): preference-data-trained BERT/MF routers, 2x cost reduction on GSM8K; direct comparison target for HYP-002"
---

## Relevance to HYP-002

RouteLLM (2024) is the most recent and strongest input-feature routing baseline, evaluated directly on GSM8K. HYP-002 claims speculative execution achieves ≥8pp more cost savings than this class of router on GSM8K.

## Key Claims

1. Routers trained on Chatbot Arena preferences achieve 2× cost reduction on MMLU, MT-Bench, and GSM8K.
2. BERT-based and matrix-factorization routers are strongest; all routes based on input features only.
3. Routers transfer well across LLM pairs, suggesting they capture query difficulty rather than model artifacts.
4. Authors note "the same question can have varying difficulty for different models" — the ambiguity speculative execution resolves.

## Gap Relevant to HYP-002

RouteLLM makes a single routing decision before generation, never observing output quality. HYP-002 always generates a cheap output and judges quality before deciding to escalate — directly observing the signal RouteLLM can only approximate. RouteLLM's GSM8K numbers provide exact baselines for HYP-002's experiment.
