---
{
  "id": "DRAFT-001",
  "type": "DraftSection",
  "created_at": "2026-04-27T05:46:39+00:00",
  "parent_ids": [
    "IDEA-001",
    "HYP-002",
    "HYP-008",
    "RES-001",
    "RES-002",
    "RES-003",
    "CRIT-007",
    "CRIT-016",
    "CRIT-017",
    "CRIT-018",
    "CRIT-019",
    "CRIT-020",
    "CRIT-021"
  ],
  "author": "paper-writer",
  "summary": "Paper outline v1: negative/preliminary results in speculative and batch LLM routing",
  "body_path": "thoughts/DRAFT-001.md",
  "section": "outline",
  "version": 1,
  "citation_ids": [],
  "text_path": "thoughts/DRAFT-001.md"
}
---

- **Claim**: We investigate whether output-quality signals (speculative cascade routing) and batch-level budget optimization (knapsack routing) can outperform simple input-feature threshold routers for multi-tier LLM routing (Haiku/Sonnet/Opus). Pre-registered experiments yield negative and preliminary results, contributing honest empirical evidence to a field dominated by positive findings.

- **Method**: We design three simulation-based experiments on GSM8K and MMLU routing scenarios: (1) an always-speculate cascade transplanting accept/reject logic from speculative decoding to model-level routing, (2) a selective speculation variant that triages queries into easy/ambiguous/hard zones before speculating, and (3) a batch knapsack router that allocates a fixed strong-model budget across queries by cost-effectiveness. All experiments use matched baselines (same noisy predictors, same quality tolerance) with 3-seed pre-registration.

- **Evidence**: EXP-001 (always-speculate) fails decisively: -5.72 +/- 1.64 pp vs the +8pp threshold, because structural overhead (Haiku+judge on every query) dominates output-quality information advantage. EXP-002 (selective speculation) shows a preliminary positive mechanism at +5.93 +/- 1.26 pp but fails the pre-registered 8pp threshold; the 95% CI straddles the threshold. EXP-003 (batch knapsack) produces an invalid negative result: a greedy knapsack mispricing bug causes pathological 75% Opus allocation, rendering the hypothesis untested rather than rejected.

- **Contributions**: (1) A structural overhead analysis showing when speculative cascade routing is viable vs input-feature routing, parameterized by cost ratio and judge quality. (2) Evidence that selective speculation (triage + speculate on ambiguous queries only) is a Pareto improvement over pure input-feature routing, though magnitude is preliminary. (3) A methodological finding that greedy knapsack formulations misprice multi-step upgrades in multi-tier settings, requiring correct marginal pricing. (4) Honest negative-result reporting with pre-registered thresholds and validity critiques.

- **Limitations**: All experiments are simulation-only (sigmoid accuracy models, no real API calls). Judge quality is assumed, not empirically validated. Statistical power is limited (3 seeds). The batch routing hypothesis remains untested in its intended form. These constraints bound the generalizability of both positive and negative findings.
