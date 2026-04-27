---
{
  "id": "CRIT-018",
  "type": "Critique",
  "created_at": "2026-04-27T05:25:58+00:00",
  "parent_ids": [
    "RES-003",
    "EXP-003",
    "HYP-008"
  ],
  "author": "critic",
  "summary": "RES-003 validity: knapsack failure is implementation bug (mispriced S→O upgrades), not valid test of batch routing; negative result does not generalize",
  "body_path": "thoughts/CRIT-018.md",
  "target_id": "RES-003",
  "mode": "validity",
  "severity": "high",
  "concerns": [
    "CRITICAL: Knapsack misprices multi-step upgrades after H→S applied",
    "Tests buggy implementation not hypothesis",
    "75% Opus allocation is pathological",
    "Simulation-only with specific cost structure",
    "High variance across 3 seeds",
    "No corrected knapsack variant tested",
    "Sanity gate tests predictor not allocation logic"
  ],
  "proposed_fix": "Do not reject HYP-008 without qualification; report mispricing bug as methodological finding; re-run with corrected marginal pricing if budget permits"
}
---

## Validity Critique: RES-003 — Batch Knapsack Routing Failure

### Verdict

RES-003's negative result (−16.75pp, batch costs MORE than independent routing) is **not a valid test of HYP-008** because the knapsack implementation contains a systematic pricing bug. The experiment's own root cause analysis identifies the problem: after H→S upgrades exhaust most of the budget, remaining H→O candidates are ranked by (P_O−P_H)/24 when the marginal cost is actually S→O=20. This mispricing is the dominant factor in the result, not a fundamental limitation of batch-level optimization.

**Severity: HIGH** — the central negative finding may be an artifact.

### Threat 1: Mispriced multi-step upgrades (severity: CRITICAL)

This is not a subtle statistical concern — it is a **bug in the optimizer**. The greedy knapsack:

1. Generates H→S candidates with efficiency (P_S−P_H)/4 and H→O candidates with efficiency (P_O−P_H)/24
2. Sorts all candidates by efficiency and greedily selects
3. H→S candidates dominate early (high efficiency) and move all queries to Sonnet
4. Remaining H→O candidates are now actually S→O upgrades (marginal cost 20, not 24)
5. But they're still ranked by H→O efficiency, which overvalues moderate queries and undervalues hard ones

The result: 75% of queries go to Opus (the most expensive tier), while the independent threshold router sends only 45-56% to Opus. The batch router *wastes budget on moderate queries* that Sonnet already handles well.

A correctly implemented knapsack would:
- Track current tier per query
- Recompute marginal efficiency after each upgrade step
- Or: enumerate S→O and H→S candidates separately with correct marginal costs

### Threat 2: Testing the bug, not the hypothesis (severity: high)

HYP-008 claims that batch-level budget awareness provides ≥20% cost advantage over per-query routing. The experiment tests whether a *specific greedy knapsack with mispriced upgrades* beats per-query routing. These are different questions. The negative result tells us that naive knapsack formulations fail in multi-tier settings — a useful finding — but does not address whether correct batch optimization outperforms independent thresholds.

### Threat 3: Pathological Opus overallocation (severity: high)

The tier distribution is a smoking gun:

| Router      | Haiku | Sonnet | Opus | Avg cost |
|-------------|-------|--------|------|----------|
| Batch       | 9.5%  | 15.5%  | 75%  | 19.7     |
| Independent | 5-8%  | 35-50% | 45-56% | 15.9-18.8 |

A budget-aware router sending 75% of queries to the most expensive tier while a simple threshold sends only ~50% is paradoxical. This alone should have triggered a validity check before reporting the result as a hypothesis rejection.

### Threat 4: Simulation limitations (severity: med, shared with RES-001/002)

Same sigmoid model, same caveats. Additionally, the 3-tier cost structure (1:5:25) represents a specific and extreme cost ratio. At more moderate ratios (e.g., 1:3:9), the mispricing effect might be smaller, and a corrected knapsack might show clearer advantage.

### Threat 5: Variance across seeds (severity: med)

Seed-level deltas range from −21.02pp (seed 42) to −11.86pp (seed 123), a nearly 2× range. This variance is driven by different noise realizations interacting with the mispricing differently — when the predictor happens to rank moderate and hard queries similarly, the mispricing has less effect. With only 3 seeds, the mean (−16.75pp) is imprecise.

### Threat 6: Sanity gate tests wrong thing (severity: low)

The sanity gate validates predictor quality (Spearman ρ=0.85 between predicted and true quality deltas). This is necessary but not sufficient: it confirms the input signal is good, but does not test whether the *allocation algorithm* uses that signal correctly. A gate that verified the knapsack's tier assignments against a known-optimal allocation would have caught the mispricing.

### Baseline parity assessment

The baseline (independent threshold router) is well-designed: same noisy predictor, same quality tolerance, exhaustive threshold sweep. The comparison is fair in the sense that both methods receive identical information. The unfairness is that the proposed method has a bug and the baseline does not.

### Recommendations for paper

1. **Do not claim batch routing is inherently inferior to independent routing.** The result is an implementation failure, not a conceptual one.
2. **Report the mispricing as the finding.** "Greedy knapsack formulations that enumerate upgrade candidates from a common base tier produce systematically wrong rankings in multi-tier settings. Correct marginal pricing is required." This is a genuine methodological contribution.
3. **If budget permits:** re-run with corrected knapsack (enumerate H→S and S→O candidates with correct marginal costs). Even if the corrected version doesn't beat independent by 20%, the comparison would be valid.
4. **If no re-run budget:** clearly label RES-003 as testing a flawed optimizer and note that HYP-008 remains untested in its intended form.
