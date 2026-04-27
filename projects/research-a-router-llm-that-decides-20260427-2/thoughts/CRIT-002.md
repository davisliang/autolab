---
{
  "id": "CRIT-002",
  "type": "Critique",
  "target_id": "HYP-006",
  "mode": "boredom",
  "severity": "high",
  "concerns": [
    "Thompson Sampling is 15-year-old, standard technique; transplant is straightforward with minimal LLM novelty",
    "Metric circularity: evaluation uses cached RouterBench outcomes, sidestepping real challenge of obtaining quality labels at inference time",
    "Weak baseline: comparing adaptive system vs frozen static router does not validate superiority vs other adaptive strategies",
    "Artificial distribution shift: MMLU→HumanEval binary split doesn't represent real-world distributional drift patterns",
    "Unfounded feedback assumption: deployed LLM quality feedback is not binary or immediate in practice; requires human eval or costly auto-eval"
  ],
  "proposed_fix": "Pivot to either: (1) contextual Thompson Sampling with learned reward model from LLM logits (not binary), or (2) compare to a simpler adaptive baseline (e.g., online logistic regression on query features), or (3) use more realistic dist-shift scenarios (e.g., temporal gradual shift via progressive benchmark mixing)"
}
---

## Critique of HYP-006: Thompson Sampling Bandit Router

### Summary
HYP-006 proposes transplanting Thompson Sampling bandits (a 15-year-old recommender-systems technique) to LLM routing under distribution shift. While the gap (online adaptation) is real, the solution is a textbook application with three critical weaknesses: circular evaluation metric (relies on cached outcomes), weak baseline (static router), and unfounded assumptions about deployment-time quality feedback.

### Core Concerns

#### 1. Straightforward, Low-Novelty Transplant
Thompson Sampling with Beta posteriors is the canonical solution for exploration-exploitation in click-through-rate prediction. Mapping {Haiku, Sonnet, Opus} → {arms} and quality → {binary reward} is a direct, no-innovation transplant. The novelty argument ("no prior LLM router paper does this") conflates "not done before" with "novel contribution." The reason prior work didn't do it isn't because the technique is sophisticated — it's because the setup (observable quality feedback) isn't standard in prior routing.

#### 2. Circular Metric: Cached Outcomes, Not Real Deployment
The experiment uses RouterBench's pre-cached correctness labels to simulate feedback. In real deployment:
- Quality labels are expensive (human eval, API calls to external evaluators)
- Feedback is sparse and delayed (you may never see labels for 80% of queries)
- The "binarization" at a quality threshold is arbitrary and metric-specific

By sidestepping these constraints, the hypothesis evaluates a fantasy scenario, not a practical system. Real online-learning routing needs a reward model trained on observed labels or LLM confidence signals, not cached ground truth.

#### 3. Weak Baseline
Comparing to a "static offline-trained router" wins trivially if distributions shift. A stronger baseline would be:
- Online logistic regression on query embeddings (learns a linear decision boundary online)
- Exponential-weights or UCB bandit (other arms of the bandit algorithm family)
- Mixture of expert routers with learned gating

The proposed baseline doesn't test whether Thompson Sampling specifically is better—it tests whether adaptation beats no adaptation, which is unsurprising.

#### 4. Artificial Distribution Shift
MMLU (QA) → HumanEval (coding) is a **hard discrete switch**, not a realistic shift. Real shifts are:
- Gradual temporal drift (user base evolves, query style changes slowly)
- Subtle topic migration (mix of benchmarks changes proportions, not categorical flip)
- Correlated shifts (if query complexity increases, cost preference may also shift)

The hypothesis doesn't characterize sensitivity to shift magnitude or gradualism.

#### 5. Unfounded Feedback Assumption
The mechanism assumes "observe quality feedback (e.g., user thumbs up/down, or auto-eval score)" is available at routing time. In practice:
- Thumbs-up/down is sparse and noisy (most users don't vote)
- Auto-eval is expensive and not available real-time for every query
- If you're paying for eval, you've already paid most of the cost to run Opus; routing becomes less important

This assumption needs justification or relaxation.

### Proposed Fix
Pivot the hypothesis to address one of:
1. **Learned reward models**: Train Thompson Sampling with a **continuous reward model** (e.g., logistic regression on query features + LLM confidence) instead of binarized cached outcomes.
2. **Realistic baselines**: Compare to online linear regression or other online learning baselines, not just a frozen router.
3. **Graduated shift**: Use progressive benchmark mixing (e.g., 10%→90% coding over query sequence) instead of a hard split.

Any of these would move the hypothesis from "apply textbook technique to new domain" to "solve a real deployment problem."
