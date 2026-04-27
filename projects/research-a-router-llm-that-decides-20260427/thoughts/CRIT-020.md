---
{
  "id": "CRIT-020",
  "type": "Critique",
  "created_at": "2026-04-27T05:43:36+00:00",
  "parent_ids": [
    "RES-002",
    "EXP-002",
    "HYP-002",
    "RES-001"
  ],
  "author": "critic",
  "summary": "RES-002 validity: positive mechanism (+5.93pp) is real but undecomposed; zone instability, fixed judge, and missing triage-only ablation prevent attribution; CI straddles threshold",
  "body_path": "thoughts/CRIT-020.md",
  "target_id": "RES-002",
  "mode": "validity",
  "severity": "med",
  "concerns": [
    "Missing triage-only ablation",
    "Fixed judge operating point not swept",
    "Ambiguous zone fraction varies 23-49%",
    "95% CI straddles 8pp threshold",
    "Simulation-only design",
    "Quality constraint margin only 0.23pp",
    "Baseline savings inconsistency vs RES-001",
    "No auto-ablation triggered"
  ],
  "proposed_fix": "Report as preliminary positive with honest CI; decompose triage vs judge contribution; flag zone instability as deployment risk; downgrade claim to suggestive"
}
---


## Validity Critique: RES-002 — Selective Speculation

### Overall Assessment

RES-002 is the most scientifically interesting result in the thread. The +5.93pp improvement over pure input-feature routing demonstrates a **genuine positive mechanism**: selective speculation (triage into easy/ambiguous/hard zones, speculate only on ambiguous) recovers the structural overhead problem that killed EXP-001. However, the result has a critical attribution gap and sits uncomfortably close to the pre-registered threshold.

### Threat 1: Missing Triage-Only Ablation (HIGH)

This is the most important validity concern. The +5.93pp conflates **two mechanisms**:
- **(a) 3-zone triage**: routing easy queries directly to Haiku and hard queries directly to Sonnet, without speculation
- **(b) Judge-based speculation**: running Haiku+judge on ambiguous queries and accepting/rejecting

Without a triage-only ablation (same 3-zone split, but ambiguous queries go to Sonnet instead of speculate), we cannot determine how much of the +5.93pp comes from mechanism (a) vs (b). This matters because:
- Mechanism (a) is a trivial extension of the baseline (add a second threshold) — zero novelty
- Mechanism (b) is the core contribution from speculative decoding transplant

If triage alone accounts for, say, 4pp and the judge adds only ~2pp, then the novel component's effect is small and fragile. The auto-ablation protocol would have caught this, but it doesn't trigger on status=fail results — a protocol gap.

### Threat 2: Ambiguous Zone Instability (MED-HIGH)

| Seed | Ambiguous zone | Delta (pp) |
|------|---------------|------------|
| 42   | 23.3%         | +6.01      |
| 123  | 49.2%         | +7.14      |
| 456  | 30.9%         | +4.63      |

The ambiguous zone fraction varies by 2x across seeds. This is driven by noise in the difficulty estimator interacting with fixed zone thresholds. In deployment:
- The router's benefit is highly sensitive to pre-screen calibration quality
- A poorly calibrated pre-screen could shrink the ambiguous zone to near-zero (judge irrelevant) or expand it excessively (re-introducing EXP-001's overhead)
- The +5.93pp average masks very different operating regimes

### Threat 3: Fixed Judge Operating Point (MED)

Unlike EXP-001 which swept judge TPR/FPR, EXP-002 fixes TPR=0.80, FPR=0.05 — a single unvalidated point. The result is conditional on this specific operating point. A modestly better judge could push delta above 8pp; a modestly worse one could erase it. The judge is the novel component — leaving its parameters unswept undermines confidence.

### Threat 4: Statistical Power at Threshold Boundary (MED)

Mean = +5.93, SD = 1.26, n = 3. Testing H0: mu >= 8 yields t = -2.84, p ~ 0.05 (one-tailed). The 95% CI [+2.78, +9.08] includes 8pp. The experiment cannot conclusively determine whether the true effect exceeds the pre-registered threshold.

### Threat 5: Simulation Fidelity (MED, inherited)

Same sigmoid model as RES-001. The 34.4% ambiguous fraction is a parameterization artifact. Real query difficulty is multimodal; the judge's marginal value depends on how many queries genuinely fall in the "could go either way" band.

### Threat 6: Quality Constraint Margin (LOW-MED)

Mean accuracy delta = -1.77pp against -2pp ceiling (0.23pp headroom). Seed 42 is at -1.97pp. In deployment with larger samples, tail degradation beyond -2pp would be more apparent.

### Threat 7: Baseline Discrepancy (LOW)

EXP-002 baseline: 17.75 +/- 1.28pp. RES-001 baseline: 18.94 +/- 0.65pp. Both use "identical" routers. The 1.2pp difference is plausible from different optimal thresholds per seed but should be verified.

### Baseline Parity

Structurally fair — same noisy predictor, same quality tolerance, exhaustive sweep. However, the proposed method adds two components (triage + judge) over the baseline's single threshold, creating an inherent complexity advantage. A 2-threshold baseline (the missing ablation) would be a fairer comparator.

### Verdict for Paper

Report as **"preliminary positive"** — not "confirmed." The +5.93pp demonstrates selective speculation is viable, but the full CI must accompany any magnitude claim. The missing triage-only ablation is a significant gap. Zone instability is a deployment consideration. The paper can claim "selective speculation outperforms pure input-feature routing" but not "output-quality signals provide >=8pp advantage."
