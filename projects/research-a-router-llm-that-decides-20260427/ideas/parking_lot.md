
## Parked at 2026-04-27T04:34:17+00:00

- `HYP-001` (idea-expander): A lightweight distilbert-based classifier routes Haiku/Sonnet/Opus more cost-efficiently than a Haiku LLM router
- `HYP-004` (idea-expander): Confidence-cascade routing with Platt-scaled dynamic thresholds reduces API cost ≥20% vs. fixed-threshold routing at matched quality
- `HYP-005` (idea-expander): 3-tier Haiku/Sonnet/Opus routing Pareto-dominates binary Haiku/Opus routing: middle tier earns its complexity by ≥3pp quality gain at ≥1 matched-cost operating point on MMLU
- `HYP-003` (idea-expander): Multi-signal routing (embedding + syntax features via logistic regression) achieves ≥85% agreement with oracle routing labels on MMLU
- `HYP-006` (idea-expander): Online contextual-bandit routing updates thresholds from deployment outcomes, achieving ≥15% additional cost reduction over static router after 500 queries on a distribution-shifted stream

## Parked at 2026-04-27T04:44:27+00:00 — cycle 1: experiments did not produce a positive result

- `HYP-002` (idea-expander): Speculative cascade execution (cross-domain transplant from speculative decoding) outperforms input-feature routing on GSM8K cost savings

## Parked at 2026-04-27T05:03:09+00:00

- `HYP-001` (idea-expander): A lightweight distilbert-based classifier routes Haiku/Sonnet/Opus more cost-efficiently than a Haiku LLM router
- `HYP-004` (idea-expander): Confidence-cascade routing with Platt-scaled dynamic thresholds reduces API cost ≥20% vs. fixed-threshold routing at matched quality
- `HYP-005` (idea-expander): 3-tier Haiku/Sonnet/Opus routing Pareto-dominates binary Haiku/Opus routing: middle tier earns its complexity by ≥3pp quality gain at ≥1 matched-cost operating point on MMLU
- `HYP-003` (idea-expander): Multi-signal routing (embedding + syntax features via logistic regression) achieves ≥85% agreement with oracle routing labels on MMLU
- `HYP-006` (idea-expander): Online contextual-bandit routing updates thresholds from deployment outcomes, achieving ≥15% additional cost reduction over static router after 500 queries on a distribution-shifted stream
- `HYP-007` (idea-expander): Conversation-history routing: rolling prior-turn difficulty features reduce strong-model calls ≥15% vs. per-query router at matched quality on simulated multi-turn MMLU

## Parked at 2026-04-27T05:26:21+00:00 — cycle 2: experiments did not produce a positive result

- `HYP-002` (idea-expander): Speculative cascade execution (cross-domain transplant from speculative decoding) outperforms input-feature routing on GSM8K cost savings
- `HYP-008` (idea-expander): Portfolio batch routing: knapsack-style budget allocation over a batch reduces API cost ≥20% vs. independent per-query routing at matched aggregate quality on RouterBench
