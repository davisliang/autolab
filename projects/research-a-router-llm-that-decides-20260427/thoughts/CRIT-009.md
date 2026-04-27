---
{
  "id": "CRIT-009",
  "type": "Critique",
  "created_at": "2026-04-27T04:59:02+00:00",
  "parent_ids": [
    "HYP-005"
  ],
  "author": "critic",
  "summary": "HYP-005 is tautological: 3-tier > 2-tier follows trivially; already proven in literature",
  "body_path": "thoughts/CRIT-009.md"
}
---

---
target_id: HYP-005
mode: boredom
severity: high
concerns:
  - "Tautological outcome: if middle tier exists at intermediate cost and captures queries where cheap models fail but expensive models not needed, Pareto domination is mathematically foregone"
  - "Already proven in literature: LIT-039 (Triage) analytically derives cost-effectiveness conditions for this exact 3-tier Haiku/Sonnet/Opus hierarchy; LIT-037 surveys multi-tier routing confirming general advantage"
  - "Lacks novel mechanism: does not propose new routing algorithm or predictor; merely validates 3-tier > 2-tier from first principles"
  - "Misidentified research question: real challenge is reliable tier prediction; validating additional tiers help capacity is design validation, not research"
proposed_fix: "Rephrase as empirical validation of whether a simple 3-class classifier can reliably predict tier membership such that Pareto advantage persists under error; or pursue novel routing mechanism (self-adaptive thresholds, online bandit) where 3-tier enables capability binary cannot"
---

## Boredom Critique: HYP-005

### Core Issue

HYP-005 claims 3-tier routing (Haiku/Sonnet/Opus) Pareto-dominates 2-tier (Haiku/Opus) by ≥3pp on MMLU. This is **tautological**: if an intermediate-cost tier exists and captures queries where weak models fail but strong models are overkill, domination follows trivially, not from research contribution.

### Literature Evidence

- **LIT-039** analytically derives when middle tier is cost-effective in exactly this setting, with formal guarantees.
- **LIT-037** surveys multi-tier routing and confirms general advantage; **LIT-038/040** demonstrate multi-tier beats single in practice.

So the core insight—"adding a tier improves Pareto frontier"—is already proven and published.

### What's Missing

The hypothesis does not propose:
- A novel routing method (new classifier or predictor design)
- New insight about query difficulty or model capability gaps
- Empirical discovery contradicting expectations

Instead, it validates an obvious design choice: 3 options beats 2 options. This is engineering validation, not research.

### Why This Matters

The real research challenge is: *given prediction error and latency constraints, does a simple 3-class classifier reliably predict tier membership to realize the Pareto gain?* That's the hypothesis worth testing. Testing whether 3-tier capacity dominates 2-tier capacity is not.

### Recommendation

**Park this hypothesis** in favor of novel-mechanism hypotheses (HYP-002, HYP-006, HYP-007, HYP-008) that offer research contributions beyond design validation.
