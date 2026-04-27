---
{
  "id": "CRIT-002",
  "type": "Critique",
  "created_at": "2026-04-27T04:30:00+00:00",
  "parent_ids": ["HYP-002"],
  "author": "screen-boredom",
  "summary": "Output-based routing already explored; judge is underspecified and domain-specific; weak baseline comparison; latency not addressed",
  "body_path": "thoughts/CRIT-HYP2.md",
  "target_id": "HYP-002",
  "mode": "boredom",
  "severity": "medium",
  "concerns": [
    "LIT-022 validates output-based routing (LLM-Blender) — the novelty claim is weakened",
    "Judge architecture is underspecified: regex+length check is domain-specific and trivial; not a scientific contribution",
    "Baseline comparison is weak: comparing to HYP-001 (DistilBERT), not RouteLLM (LIT-020, SOTA) which achieves 2x cost reduction on GSM8K",
    "Latency is a critical practical concern but listed only as open question; speculative execution inherently serializes (Haiku→judge→Sonnet), risking latency regression",
    "Scope is narrow: evaluated only on GSM8K (math). Cross-domain applicability to MMLU/general QA is unclear; limits generalizability"
  ],
  "proposed_fix": "Strengthen via: (a) Judge design—train a learned verifier (PRM or embeddings-based confidence) rather than regex; (b) Scope—evaluate on GSM8K + MMLU to validate transplant generality; (c) Metrics—include latency/throughput as primary, not just cost"
}
---

## Boredom Critique: HYP-002

### Core Risk: Output-Based Routing Is Established, Judge Design Is Trivial

HYP-002 frames speculative model execution as novel by transposing speculative decoding from token→model level. The claim rests on two pillars: (1) observing outputs before routing is better than input-feature routing, and (2) a lightweight judge can reliably detect when to escalate.

**Problem:** Pillar 1 is already validated (LIT-022). Pillar 2—the judge design—is relegated to a regex check, which is neither novel nor generalizable.

### Evidence

**1. Output-based routing is not new (LIT-022)**
- LLM-Blender PairRanker explicitly routes based on model outputs
- The premise of HYP-002—"output quality beats input features"—is already proven
- Novelty claim depends on the judge design, not the routing paradigm

**2. Judge architecture is underspecified and domain-specific**
- Proposed: "regex answer extraction + chain-of-thought length check"
- This is not a research contribution; it's a heuristic
- Works only for math (extractable final answers); breaks on MMLU, reasoning, open-ended tasks
- No learned component; no calibration; no transferability

**3. Weak baseline**
- Compares against HYP-001 (DistilBERT feature router)
- RouteLLM (LIT-020) is the actual SOTA on GSM8K: 2x cost reduction
- If HYP-002 is tested against a suboptimal baseline, the 8pp improvement is an artifact, not a win

**4. Latency is a blocker, not an open question**
- Speculative execution is inherently sequential: Haiku inference → judge → escalation to Sonnet
- Latency regression is the dominant risk; measuring it is not optional
- If response time doubles while cost drops 5%, the system is not practical

**5. Scope is too narrow**
- GSM8K alone cannot validate cross-domain transplant claims
- Router robustness is assessed on MMLU, HELM, or multi-domain splits
- Single-domain success is easier to achieve and less surprising

### Recommendation

**Park HYP-002 unless:** Pick one path:
- **A (Strong judge):** Design a learned verifier (process reward model, embeddings-based confidence, or fine-tuned rejection detector) that generalizes beyond regex. Make the judge a research contribution.
- **B (Broad scope):** Evaluate on GSM8K + MMLU. Validate that speculative execution generalizes across domains, not just math.
- **C (Latency metric):** Include latency/throughput as a co-primary metric. Frame as a Pareto trade-off study, not just cost savings.

Without one of these, HYP-002 is a routine engineering experiment comparing a weak baseline.
