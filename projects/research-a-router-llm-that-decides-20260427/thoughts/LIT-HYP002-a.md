---
id: LIT-HYP002-a
type: LitFinding
arxiv_id: "2211.17192"
title: "Fast Inference from Transformers via Speculative Decoding"
relevance: 0.95
parent_ids: ["HYP-002"]
author: literature-scout
summary: "Source-domain for HYP-002 cross-domain transplant: token-level speculative accept/reject (Leviathan et al. 2023) lifted to model-level cascade"
---

## Relevance to HYP-002

The foundational speculative decoding paper whose core mechanism HYP-002 directly transplants. A fast "draft" model generates tokens speculatively; a large "verifier" accepts/rejects via modified rejection sampling, achieving the verifier's distribution at draft speed.

## Key Claims

1. Hard LM tasks embed easier subtasks approximable by efficient models — exactly the difficulty asymmetry HYP-002 exploits (easy GSM8K → Haiku, hard → Sonnet).
2. Accept/reject protocol preserves the target model's output distribution exactly; no quality degradation.
3. 2-3× speedup on T5-XXL without retraining.
4. Draft acceptance rate is the central efficiency variable — directly analogous to "fraction of Haiku answers accepted by judge" in HYP-002.

## Gap Relevant to HYP-002

Speculative decoding operates token-level between same-architecture models with probability-based acceptance. HYP-002 transplants: (1) from token level to model level, (2) from same-architecture to cross-provider (Haiku→Sonnet), (3) from probability acceptance to task-level quality judge. This is novel and no prior work has executed this transplant.
