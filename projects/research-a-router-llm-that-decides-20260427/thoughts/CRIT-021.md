---
{
  "id": "CRIT-021",
  "type": "Critique",
  "created_at": "2026-04-27T05:44:19+00:00",
  "parent_ids": [
    "RES-003",
    "EXP-003",
    "HYP-008"
  ],
  "author": "critic",
  "summary": "RES-003 validity: negative result is implementation artifact (mispriced marginal upgrades), not valid test of HYP-008; 75% Opus allocation is pathological proof of bug",
  "body_path": "thoughts/CRIT-021.md",
  "target_id": "RES-003",
  "mode": "validity",
  "severity": "high",
  "concerns": [
    "CRITICAL: Greedy knapsack misprices S->O upgrades after H->S step",
    "75% Opus allocation is pathological",
    "Tests buggy optimizer not hypothesis",
    "Sanity gate validates predictor not allocation",
    "No corrected knapsack tested",
    "High variance across 3 seeds reflects bug sensitivity",
    "Simulation-only with extreme cost ratio",
    "HYP-008 should be marked untested not rejected"
  ],
  "proposed_fix": "Do not reject HYP-008; report mispricing as methodological finding; label result as testing flawed optimizer; note hypothesis remains open"
}
---


## Validity Critique: RES-003 — Batch Knapsack Routing Failure

### Overall Assessment

RES-003's negative result (-16.75pp; batch costs MORE than independent routing) is **not a valid test of HYP-008**. The experiment's own root cause analysis identifies a systematic pricing bug in the greedy knapsack: after H->S upgrades move all queries to Sonnet, remaining H->O candidates are ranked by their original H->O efficiency instead of the actual S->O marginal cost. This is not a subtle statistical concern — it is an **optimizer bug** that produces a pathological 75% Opus allocation rate.

**Severity: HIGH.** The central negative finding is an artifact of the implementation, not evidence against batch-level routing.

### Threat 1: Mispriced Multi-Step Upgrades (CRITICAL)

The greedy knapsack generates candidates:
- H->S: efficiency = (P_S - P_H) / 4
- H->O: efficiency = (P_O - P_H) / 24

After sorting by efficiency, H->S candidates dominate and exhaust budget first, moving all queries to Sonnet. Remaining "H->O" candidates are now effectively S->O upgrades, but still ranked by (P_O-P_H)/24 instead of the correct (P_O-P_S)/20.

**The mispricing inverts priority rankings:**

| Query type | (P_O-P_H)/24 rank | (P_O-P_S)/20 rank | Correct action |
|-----------|-------------------|-------------------|----------------|
| Moderate (d~0.45) | HIGH (0.031) | LOW (0.009) | Stay at Sonnet |
| Hard (d~0.65) | LOW (0.026) | HIGH (0.021) | Upgrade to Opus |

The knapsack upgrades moderate queries (where Sonnet is already adequate) while leaving hard queries (where Opus genuinely helps) at Sonnet. This is exactly backwards.

Result: 75% Opus allocation vs the independent router's 45-56%.

### Threat 2: Testing the Bug, Not the Hypothesis (HIGH)

HYP-008 claims batch-level budget awareness provides >=20% cost advantage over per-query routing. The experiment tests whether a specific greedy knapsack with mispriced marginal costs beats per-query routing. These are different questions.

A correctly implemented batch router would:
1. Track each query's current tier assignment
2. Enumerate only valid marginal upgrades (H->S, S->O) with correct marginal costs
3. Or use a proper LP/MILP formulation that avoids the greedy two-step error

The negative result tells us naive knapsack formulations fail in multi-tier settings — useful but not what HYP-008 asked.

### Threat 3: Pathological Tier Distribution (HIGH — diagnostic)

| Router      | Haiku | Sonnet | Opus  | Avg cost |
|-------------|-------|--------|-------|----------|
| Batch       | 9.5%  | 15.5%  | 75.0% | 19.7     |
| Independent | 5-8%  | 35-50% | 45-56%| 15.9-18.8|

A router claiming to optimize cost while sending 75% of queries to the most expensive tier is self-evidently broken. This distribution should have been a red flag before reporting the result as a hypothesis rejection.

### Threat 4: Sanity Gate Tests Wrong Property (MED)

The gate validates predictor quality (Spearman rho=0.85). This confirms the input signal is good but tests nothing about the allocation algorithm. A gate verifying knapsack assignments against a known-optimal toy allocation would have caught the mispricing.

### Threat 5: Variance and Seed Sensitivity (MED)

| Seed | Delta vs independent (pp) |
|------|--------------------------|
| 42   | -21.02                    |
| 123  | -11.86                    |
| 456  | -17.37                    |

The nearly 2x range reflects the bug's sensitivity to noise realizations. With only 3 seeds the mean is imprecise, but this is moot given the implementation flaw.

### Threat 6: Cost Ratio Amplification (LOW-MED)

The 1:5:25 cost structure creates a 5x gap between Sonnet and Opus, magnifying the mispricing. At more moderate ratios the effect would be smaller. But this is moot given the bug.

### Baseline Parity

The baseline (independent threshold router) is well-designed: identical noisy predictor, same quality tolerance, exhaustive sweep. The comparison is structurally fair. The unfairness is that the proposed method has an implementation bug and the baseline does not.

### Verdict for Paper

1. **Do not reject HYP-008.** Label as "open/untested" rather than "rejected."
2. **Report mispricing as methodological contribution.** Greedy knapsack formulations that enumerate from a common base tier produce systematically wrong rankings in multi-tier settings. Correct marginal pricing is required.
3. **Report 75% Opus allocation as diagnostic red flag** for future batch routing work.
4. **If budget permits**, re-run with corrected marginal pricing for a valid test.
5. **If no re-run budget**, clearly state RES-003 tests a flawed optimizer and the hypothesis remains open.
