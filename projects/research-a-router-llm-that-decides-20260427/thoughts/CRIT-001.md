---
{
  "id": "CRIT-001",
  "type": "Critique",
  "created_at": "2026-04-27T00:19:03+00:00",
  "parent_ids": [
    "HYP-003"
  ],
  "author": "screen-boredom",
  "summary": "Speculative routing cost-latency tradeoff breaks CPU analogy; misprediction penalty makes 15% latency target unrealistic",
  "body_path": "thoughts/CRIT-001.md",
  "mode": "boredom",
  "severity": "high",
  "target_id": "HYP-003",
  "concerns": "Speculative execution (CPU analogy) is already well-established in LLM token generation (LIT-010 Speculative Decoding, LIT-012 Speculative Sampling). The transplant to routing adds a critical flaw: mispredictions incur real API costs (wasted Haiku tokens), unlike zero-cost CPU branch mispredictions. At 70% router accuracy, 30% of queries waste Haiku call cost with no benefit. The latency bottleneck in existing cascades (RouteLLM, FrugalGPT) is the small-model call itself (~T_haiku), not the router. Parallelizing a 5ms router with a 2-5s Haiku call does not save latency in the critical case: if router says Sonnet/Opus, you still pay full escalation latency AND the wasted Haiku cost. 15% latency target unrealistic when cost penalty likely exceeds any latency win.",
  "proposed_fix": "Park this hypothesis. The cost-latency tradeoff fundamentally breaks the CPU analogy. Consider instead: (a) better router accuracy to reduce misprediction cost, or (b) caching/memoization to reduce small-model call latency without the wasted-call penalty."
}
---

