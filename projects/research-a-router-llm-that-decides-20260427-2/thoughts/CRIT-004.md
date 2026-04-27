---
{
  "id": "CRIT-004",
  "type": "Critique",
  "created_at": "2026-04-27T01:57:16+00:00",
  "parent_ids": [
    "HYP-002"
  ],
  "author": "critic",
  "summary": "HYP-002 cascade router: intrinsic confidence triggers are incremental vs FrugalGPT/AutoMix/ASR precedent",
  "body_path": "thoughts/CRIT-004.md",
  "target_id": "HYP-002",
  "mode": "boredom",
  "severity": "medium",
  "concerns": [
    "Cascade observe-then-escalate validated by FrugalGPT (98% cost reduction) and AutoMix (50%+)",
    "LIT-020 provides exact ASR blueprint for confidence-triggered cascade",
    "Main novelty (intrinsic vs external confidence) is narrow methodological variation",
    "15% improvement threshold modest vs FrugalGPT baseline; incremental gains in explored space"
  ],
  "proposed_fix": "Investigate whether intrinsic-signal cascades outperform learned external scorers by convincing margin, OR pivot to genuinely novel cascade variant (multi-stage per-token tracking, adaptive threshold scheduling, confidence-weighted fusion)."
}
---

# Critique: HYP-002 Confidence-Cascade Router

## Assessment: Medium Boredom

HYP-002 proposes a confidence-cascade router where small models self-assess via intrinsic signals (logprobs, entropy) and escalate to larger models when confidence is low, targeting ≥15% cost-normalized quality improvement over static routers.

## Concerns

1. **Cascade paradigm already validated**: FrugalGPT (LIT-019) validates the observe-then-escalate paradigm achieving 98% cost reduction via adaptive query triage. The core insight—that cascading is superior to upfront routing—is established.

2. **Exact blueprint exists**: LIT-020 (Two-Pass End-to-End ASR) provides the precise cross-domain template HYP-002 transplants: streaming attempt + beam-score-triggered escalation to a more powerful model.

3. **Existing cascade variants already tested**: AutoMix (LIT-021) demonstrates cascade + self-verification achieving 50%+ cost savings. The cascade mechanism is not novel.

4. **Main novelty is narrow**: HYP-002's central contribution—substituting *intrinsic* confidence signals (logprobs, entropy) for *external* verifiers or learned scorers—is a methodological tweak on a well-established pattern. LIT-017 confirms LLM self-reported confidence is well-calibrated, so this substitution does not introduce surprising risk.

5. **Improvement threshold is modest**: ≥15% cost-normalized quality gain is incremental against FrugalGPT's 98% cost reduction and AutoMix's 50%+ savings, suggesting the hypothesis may be seeking marginal gains in a well-explored design space.

## Proposed Fix

Either:
- Investigate whether intrinsic-signal cascades statistically outperform *learned* external scorers (e.g., RouteLLM feature vectors used in FrugalGPT) by a convincing margin to justify the hypothesis; OR
- Pivot toward a genuinely novel cascade variant (e.g., multi-stage per-token confidence tracking, learned adaptive threshold scheduling, or confidence-weighted fusion rather than hard escalation).

