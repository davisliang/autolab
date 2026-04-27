---
{
  "id": "CRIT-017",
  "type": "Critique",
  "created_at": "2026-04-27T05:25:48+00:00",
  "parent_ids": [
    "RES-002",
    "EXP-002",
    "HYP-002",
    "RES-001"
  ],
  "author": "critic",
  "summary": "RES-002 validity: selective speculation shows real mechanism (+5.93pp) but simulation-only design, fixed judge params, and zone instability undermine precise claims",
  "body_path": "thoughts/CRIT-017.md",
  "target_id": "RES-002",
  "mode": "validity",
  "severity": "med",
  "concerns": [
    "Simulation-only sigmoid model",
    "Fixed judge operating point (TPR=0.8, FPR=0.05) not swept",
    "Ambiguous zone fraction varies 23-49% across seeds",
    "Missing ablation: triage vs judge contribution not decomposed",
    "3 seeds; 95% CI straddles 8pp threshold",
    "Baseline savings discrepancy vs RES-001",
    "Quality constraint margin only 0.23pp"
  ],
  "proposed_fix": "Report as preliminary positive; flag zone instability; decompose triage vs judge contribution; note CI includes threshold"
}
---

## Validity Critique: RES-002 — Selective Speculation

### Verdict

RES-002 shows a **genuine positive mechanism** (+5.93pp over pure input-feature routing) but **fails the pre-registered 8pp threshold**. The result is more interesting than RES-001's clean failure — it demonstrates that selective speculation (triage + speculate only on ambiguous queries) recovers the structural overhead problem. However, the precise magnitude is unreliable, and the 95% CI actually straddles the threshold.

### Threat 1: Simulation fidelity (severity: high, inherited from RES-001)

Same sigmoid accuracy model, same concerns. The ambiguous zone (where the judge operates) is defined by difficulty thresholds derived from the Beta(2,3) distribution. Real query difficulty distributions are multimodal and task-dependent; the fraction of queries in the ambiguous zone — and therefore the magnitude of the judge's contribution — is distribution-dependent. The 34.4% mean ambiguous fraction is an artifact of the parameterization, not an empirical finding.

### Threat 2: Fixed judge operating point (severity: med)

Unlike EXP-001 which swept judge TPR/FPR, EXP-002 fixes TPR=0.80, FPR=0.05. This is a single point on the ROC curve. A better judge (TPR=0.90, FPR=0.03) could push the delta above 8pp; a worse one could erase it. The result is conditional on this specific operating point being realistic, which is unvalidated.

### Threat 3: Ambiguous zone instability (severity: med)

The ambiguous zone fraction varies from 23.3% (seed 42) to 49.2% (seed 123) — a 2× range. This means the mechanism's applicability is highly sensitive to the noise realization in the difficulty estimator. In deployment, this corresponds to: "the router's benefit depends heavily on how well the pre-screen calibrates the ambiguous band." This is not a fatal flaw, but it means the +5.93pp is an average over very different operating regimes.

| Seed | Ambig zone | Delta |
|------|-----------|-------|
| 42   | 23.3%     | +6.01 |
| 123  | 49.2%     | +7.14 |
| 456  | 30.9%     | +4.63 |

Interestingly, seed 123 (largest zone) also has the largest delta — suggesting more queries in the zone means more opportunity for the judge. But with n=3, this correlation is not statistically meaningful.

### Threat 4: Missing ablation — triage vs judge decomposition (severity: med)

The +5.93pp improvement over pure input-feature routing conflates two mechanisms: (a) the 3-zone triage itself (easy→Haiku, hard→Sonnet, ambiguous→speculate) and (b) the judge within the ambiguous zone. Without an ablation that uses the same triage but routes ambiguous queries to Sonnet directly (no speculation), we cannot attribute the improvement. It's possible that the triage alone (a simple extension of the baseline) captures most of the gain, and the judge adds little. This matters because the judge is the novel component.

### Threat 5: Statistical power at the threshold boundary (severity: med)

Mean = +5.93, stddev = 1.26, n = 3. The t-statistic for testing H₀: μ ≥ 8 is t = (5.93 − 8) / (1.26/√3) = −2.84, p ≈ 0.05 (one-tailed). This *barely* rejects at α = 0.05, but the 95% CI for the mean [+2.78, +9.08] includes 8pp. The experiment cannot conclusively determine whether the true effect is above or below the threshold. More seeds would resolve this.

### Threat 6: Baseline discrepancy (severity: low)

EXP-002 reports baseline_savings_pp = 17.75 ± 1.28, while RES-001 reported baseline_savings_pp = 18.94 ± 0.65. Both use the "same" input-feature router with the same parameters. The difference likely reflects different optimal threshold selections across the sweep for each seed draw, which is valid — but the magnitude difference (1.2pp) is notable for a supposedly identical baseline and should be verified.

### Threat 7: Quality constraint margin (severity: low)

Mean accuracy delta = −1.77pp against a −2pp ceiling. This leaves only 0.23pp of headroom. Per-query, some queries necessarily degrade more than 2pp while others improve — no distributional analysis is provided. In deployment, the tail of quality degradation matters more than the mean.

### Baseline parity assessment

The baseline is the same pure input-feature router as EXP-001, applied to the same simulated dataset. The comparison is structurally fair. However, the proposed method adds two components (triage + judge) over the baseline's single threshold, creating an inherent complexity advantage that should be acknowledged.

### Recommendations for paper

1. Report as **"preliminary positive"** — the mechanism works but magnitude is uncertain.
2. The +5.93pp should be accompanied by the full CI and a note that it does not conclusively clear 8pp.
3. Decompose the contribution: what fraction of the gain comes from triage vs judge?
4. Flag zone fraction instability as a deployment consideration.
5. Per auto-ablation protocol: no ablation was run (status=fail triggers no auto-ablation), but a triage-only ablation would strengthen the finding.
