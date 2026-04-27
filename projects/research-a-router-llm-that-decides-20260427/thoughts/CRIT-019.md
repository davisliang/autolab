---
{
  "id": "CRIT-019",
  "type": "Critique",
  "created_at": "2026-04-27T05:42:51+00:00",
  "parent_ids": [
    "RES-001",
    "EXP-001",
    "HYP-002"
  ],
  "author": "critic",
  "summary": "RES-001 validity: structural overhead argument is sound but magnitude unquantifiable from simulation; 3 compounding threats prevent confident rejection of HYP-002",
  "body_path": "thoughts/CRIT-019.md",
  "target_id": "RES-001",
  "mode": "validity",
  "severity": "med",
  "concerns": [
    "Simulation-only design",
    "Assumed judge ROC without calibration",
    "Trivial sanity gate",
    "3 seeds with wide CI",
    "Single cost ratio tested",
    "Sigmoid model ignores correlated failures",
    "No latency accounting"
  ],
  "proposed_fix": "Accept directional finding; report magnitude as approximate; add cost-ratio sensitivity; acknowledge judge ROC as pivotal unknown"
}
---


## Validity Critique: RES-001 — Speculative Cascade Failure

### Overall Assessment

The negative result (−5.72pp vs ≥+8pp threshold) is **directionally credible** but **magnitude-uncertain**. The core structural argument — that always-speculate pays Haiku+judge on every query, making escalated queries 24% more expensive than direct Sonnet — is a mathematical identity independent of simulation fidelity. This alone justifies a directional conclusion. What cannot be trusted is the precise gap.

### Threat 1: Simulation-Only Design (HIGH)

No real model was called. The entire experiment operates on synthetic difficulty draws from Beta(2,3) with sigmoid accuracy curves. Real GSM8K exhibits:
- **Bimodal difficulty**: many trivially easy problems and a cluster of genuinely hard multi-step problems, not a smooth Beta distribution
- **Correlated model failures**: Haiku and Sonnet share training data; when Haiku fails on a problem, Sonnet is more likely to fail too than independence assumes. This inflates the "needed escalation" rate, worsening cascade economics
- **Format-dependent errors**: correct reasoning with wrong answer extraction, which a regex judge would catch but the simulation's binary correctness model cannot represent

The simulation is a reasonable sketch but cannot ground the −5.72pp number.

### Threat 2: Assumed Judge ROC (MED)

The judge is parameterized as a linear TPR/FPR sweep with no empirical basis. HYP-002 proposed a regex+CoT-length judge for math, which on structured GSM8K problems could plausibly achieve TPR≥0.90 at FPR≤0.03 — well above the best simulated operating point. At those parameters, more Haiku answers are correctly accepted, reducing escalation frequency and potentially flipping the sign of the result. The negative finding is **conditional on a mediocre judge**, but the hypothesis proposed a domain-specific judge. This is the single most important unresolved variable.

### Threat 3: Trivial Sanity Gate (MED)

The gate computes predictions as 0.3*random + 0.7*labels + noise, guaranteeing ~80% cross-entropy loss drop by construction. It tests nothing about the experimental apparatus — not the router, not the judge, not the simulation model. A meaningful gate would have tested above-chance discrimination on held-out difficulty draws.

### Threat 4: Statistical Power (LOW-MED)

Three seeds produce −5.72 ± 1.64pp (95% CI ≈ [−9.4, −2.0]). The CI excludes zero and the +8pp threshold, so the directional conclusion is statistically sound. However, the 7pp-wide interval means we cannot distinguish "cascade is slightly worse" from "cascade is dramatically worse" — relevant for judging whether a better judge could close the gap.

### Threat 5: Single Cost Ratio (LOW)

The experiment tests only cost ratio 1:5 (Haiku:Sonnet). At 1:10, escalation overhead drops from 24% to 12%, lowering the break-even acceptance rate. At 1:3, overhead rises to 40%. No sensitivity analysis was performed. Generalizability beyond the specific parameterization is unestablished.

### Threat 6: Missing Correlated-Failure Modeling (LOW)

The simulation draws Haiku and Sonnet outcomes independently given difficulty. In reality, shared pretraining creates positive outcome correlation. This increases wasted escalation (both fail) and decreases productive escalation (only Haiku fails). Net effect: makes the cascade look worse than in the simulation. The directional finding would be reinforced, but the simulation underestimates this effect.

### Baseline Parity

**Fair.** Both strategies receive identical difficulty draws and model outcomes. Quality tolerance (≤2pp vs Sonnet-only) applied symmetrically. The input-feature router baseline uses the same noise level and an exhaustive threshold sweep. Within the simulation framework, the comparison is unbiased.

### Verdict for Paper

RES-001 establishes that naïve always-speculate cascading loses to input-feature routing under plausible parameterizations. The structural overhead argument is the primary contribution (mathematical, not simulation-dependent). Report the −5.72pp as indicative, not definitive. Note that a stronger domain-specific judge or lower cost ratio could shift the outcome — this motivates EXP-002's selective speculation approach.
