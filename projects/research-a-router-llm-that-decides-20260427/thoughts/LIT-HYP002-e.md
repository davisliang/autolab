---
id: LIT-HYP002-e
type: LitFinding
arxiv_id: "2305.20050"
title: "Let's Verify Step by Step"
relevance: 0.75
parent_ids: ["HYP-002"]
author: literature-scout
summary: "Process reward models (PRMs) outperform outcome-only verification for math reasoning; directly informs HYP-002 answer-quality judge design and failure modes"
---

## Relevance to HYP-002

HYP-002 requires a lightweight answer-quality judge to accept/reject Haiku's GSM8K outputs. Lightman et al. show process supervision (step-level feedback) substantially outperforms outcome supervision for math quality verification — informing judge design choices.

## Key Claims

1. PRMs (step-level feedback) solve 78% of MATH test-set problems vs. ~56% for outcome-supervised models.
2. Step-level verification catches errors where the final answer looks correct but reasoning is wrong.
3. Outcome supervision (checking final answer only) is a weak signal for math reasoning quality.
4. PRM800K provides 800K step-level labels (training cost is high for lightweight deployment).

## Gap Relevant to HYP-002

HYP-002's judge uses only regex answer extraction + CoT-length check — a pure outcome judge. This paper predicts it will have a high false-accept rate on answers with correct-looking numbers but wrong reasoning. However, GSM8K is simpler than MATH (elementary arithmetic), so outcome-only may suffice. If accuracy degradation > 2pp, a PRM-style judge upgrade is the primary mitigation. This risk is tracked as an open question in HYP-002.
