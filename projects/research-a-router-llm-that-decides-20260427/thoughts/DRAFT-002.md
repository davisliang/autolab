---
{
  "id": "DRAFT-002",
  "type": "DraftSection",
  "created_at": "2026-04-27T05:48:44+00:00",
  "parent_ids": [
    "DRAFT-001",
    "IDEA-001",
    "HYP-002",
    "HYP-008",
    "RES-001",
    "RES-002",
    "RES-003",
    "CRIT-017",
    "CRIT-019",
    "CRIT-020",
    "CRIT-021"
  ],
  "author": "paper-writer",
  "summary": "Abstract v1: negative and preliminary results on speculative cascade and batch knapsack LLM routing",
  "body_path": "thoughts/DRAFT-002.md",
  "section": "abstract",
  "version": 1,
  "citation_ids": [
    "CITE-006",
    "CITE-008",
    "CITE-009"
  ],
  "text_path": "thoughts/DRAFT-002.md"
}
---


## Abstract

Multi-tier LLM routing—deciding per query whether to invoke a cheap, moderate, or expensive model—promises large cost savings at minimal quality loss. Existing routers rely on input features to classify query difficulty before generation \cite{chen2023frugalgpt, ong2024routellm}. We ask whether two alternative strategies can outperform this approach: (1) *speculative cascade routing*, a cross-domain transplant from speculative decoding \cite{leviathan2023fast} that runs a cheap model first and escalates based on output-quality signals, and (2) *batch knapsack routing*, which allocates a fixed strong-model budget across a query batch by predicted quality gain per dollar.

We conduct pre-registered simulation experiments on GSM8K (1,319 questions) and MMLU (1,000 questions) with three-seed replication and matched baselines. Our results are primarily negative. The always-speculate cascade (EXP-001) loses 5.72 $\pm$ 1.64 percentage points in cost savings versus the input-feature baseline, because the structural overhead of running a cheap model plus judge on every query (24\% cost premium on escalated queries) outweighs the information advantage of observing output quality. A refined *selective speculation* variant (EXP-002) that triages queries into easy, ambiguous, and hard zones before speculating recovers this deficit and achieves a preliminary +5.93 $\pm$ 1.26 pp improvement, but fails the pre-registered $\geq$8 pp threshold (95\% CI: [2.78, 9.08]). The batch knapsack experiment (EXP-003) produces an invalid negative result due to a systematic marginal-pricing bug: the greedy optimizer misprices multi-step tier upgrades, yielding a pathological 75\% Opus allocation; we report this as a methodological finding rather than a hypothesis rejection.

Our contributions are: (1) a structural overhead analysis parameterizing when speculative cascade routing can break even against input-feature routing as a function of cost ratio and judge quality; (2) preliminary evidence that selective speculation—restricting output-quality verification to an ambiguous query zone—is a Pareto improvement over pure input-feature routing; (3) identification of a marginal-pricing failure mode in greedy knapsack formulations for multi-tier routing; and (4) honest negative-result reporting with pre-registered thresholds, validity critiques, and reproducible simulation code.
