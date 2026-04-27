---
{
  "id": "CRIT-016",
  "type": "Critique",
  "created_at": "2026-04-27T05:25:39+00:00",
  "parent_ids": [
    "RES-001",
    "EXP-001",
    "HYP-002",
    "CRIT-007"
  ],
  "author": "critic",
  "summary": "RES-001 validity: negative result directionally sound but magnitude untrustworthy; simulation-only + assumed judge ROC + no cost-ratio sensitivity",
  "body_path": "thoughts/CRIT-016.md",
  "target_id": "RES-001",
  "mode": "validity",
  "severity": "med",
  "concerns": [
    "Simulation-only sigmoid model",
    "Assumed judge ROC parameterization",
    "Trivial sanity gate",
    "3 seeds with wide CI",
    "No cost-ratio sensitivity",
    "No latency analysis"
  ],
  "proposed_fix": "Report magnitude as approximate; add cost-ratio sweep; note real judge ROC could shift crossover"
}
---

## Validity Critique: RES-001 — Speculative Cascade Failure

### Verdict

The negative result (−5.72pp vs +8pp threshold) is **directionally trustworthy** but the **precise magnitude is unreliable**. The structural overhead argument — that always paying Haiku+judge (1.2 units) makes escalated queries 24% more expensive than direct Sonnet — is a mathematical identity that holds regardless of simulation fidelity. The experiment correctly identifies *why* the cascade fails. Where it falls short is quantifying *how badly* it fails.

### Threat 1: Simulation fidelity (severity: high)

The sigmoid accuracy model (Haiku center=0.35, Sonnet center=0.60, slope=0.05) produces smooth monotonic difficulty-accuracy curves. Real GSM8K exhibits: (a) discontinuous difficulty jumps between problem types, (b) correlated model failures (Haiku and Sonnet fail on the same problems more often than independence would predict, since they share training data), (c) format-dependent failures where a correct solution is marked wrong due to answer extraction. These factors could either widen or narrow the gap — the simulation cannot distinguish.

### Threat 2: Assumed judge ROC (severity: med)

The judge TPR/FPR are swept along `fpr = 0.02 + 0.13*(tpr-0.60)/0.35`, a linear parameterization with no empirical basis. HYP-002 proposed a regex+CoT-length judge, which on structured math problems could plausibly achieve TPR≥0.90 at FPR≤0.03 — well above the assumed ROC. At those operating points, the cascade accepts more Haiku answers correctly, potentially closing the 5.7pp gap. The negative result is conditional on assumed judge quality.

### Threat 3: Trivial sanity gate (severity: med)

The sanity gate computes `trained_preds = 0.3 * random + 0.7 * labels + noise`, guaranteeing ~80% loss drop by construction. It validates nothing about the experimental apparatus. A meaningful gate would have tested whether the router or judge achieves above-chance discrimination on held-out difficulty draws.

### Threat 4: Statistical power (severity: low)

Three seeds yield −5.72 ± 1.64pp. The 95% CI is approximately [−9.4, −2.0] — it excludes zero and the +8pp threshold, so the directional conclusion (cascade worse than baseline) is statistically sound. But the magnitude estimate spans a 7pp range, which matters for determining how far the approach is from viability.

### Threat 5: Missing cost-ratio sensitivity (severity: low)

At cost ratio 1:10 (plausible for some API pricing tiers), escalation overhead drops from 24% to 12%, and the break-even acceptance rate falls. No sweep was performed. This matters for generalizability beyond the specific 1:5 parameterization.

### Baseline parity assessment

**No concerns.** Both strategies see identical difficulty draws and model outcomes per seed. The quality tolerance constraint (≤2pp accuracy drop vs Sonnet-only) is applied symmetrically. The input-feature router baseline uses reasonable noise and threshold sweep. The comparison is fair within the simulation's assumptions.

### Recommendations for paper

1. Report the structural overhead argument as the primary finding (mathematical, not simulation-dependent).
2. Cite the −5.72pp magnitude as **approximate** and simulation-specific.
3. Note boundary conditions: at lower cost ratios or with a stronger judge, the cascade could become competitive.
4. CRIT-007 raised the same core concerns — this critique reinforces rather than contradicts.
