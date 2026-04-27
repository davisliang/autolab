---
id: LIT-HYP002-b
type: LitFinding
arxiv_id: "2302.01318"
title: "Accelerating Large Language Model Decoding with Speculative Sampling"
relevance: 0.80
parent_ids: ["HYP-002"]
author: literature-scout
summary: "Independent confirmation of speculative decoding (Chen et al. / DeepMind 2023): 2-2.5x speedup; acceptance rate key; heterogeneous difficulty queries benefit most"
---

## Relevance to HYP-002

Independent DeepMind development of speculative sampling with identical core mechanism to Leviathan et al. Draft proposes; large model accepts/rejects in parallel via modified rejection sampling. Chinchilla 70B achieves 2-2.5× speedup.

## Key Claims

1. Parallel scoring latency ≈ single-token large model latency — speculation is worthwhile if acceptance rate is high enough.
2. Technique most effective when query difficulty is heterogeneous — matches GSM8K's bimodal easy/hard distribution.
3. Acceptance rate collapses speedup when draft/target frequently disagree.
4. Modified rejection sampling provably preserves target distribution.

## Gap Relevant to HYP-002

Both speculative decoding papers require token-probability access (same provider, same architecture family). HYP-002's key contribution: enable speculation across providers (Anthropic Haiku→Sonnet) where token probabilities are unavailable, replacing probability acceptance with a task-level answer quality judge.
