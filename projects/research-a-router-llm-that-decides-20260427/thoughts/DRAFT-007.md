---
{
  "id": "DRAFT-007",
  "type": "DraftSection",
  "created_at": "2026-04-27T06:07:00+00:00",
  "parent_ids": [
    "DRAFT-001",
    "DRAFT-005",
    "DRAFT-006",
    "RES-001",
    "RES-002",
    "RES-003",
    "CRIT-016",
    "CRIT-017",
    "CRIT-018",
    "CRIT-019",
    "CRIT-020",
    "CRIT-021",
    "HYP-002",
    "HYP-008"
  ],
  "author": "paper-writer",
  "summary": "Discussion v1: interprets negative/preliminary results, structural overhead analysis, methodological lessons, limitations, and future directions",
  "body_path": "thoughts/DRAFT-007.md",
  "section": "discussion",
  "version": 1,
  "citation_ids": [
    "CITE-006",
    "CITE-007",
    "CITE-008",
    "CITE-009",
    "CITE-011",
    "CITE-017",
    "CITE-023",
    "CITE-025",
    "CITE-031",
    "CITE-033"
  ],
  "text_path": "thoughts/DRAFT-007.md"
}
---

## 6. Discussion

Our experiments yield two negative results and one preliminary positive, none of which confirm the pre-registered hypotheses at their stated thresholds. Rather than view these as failures, we argue they expose structural properties of the multi-tier routing problem that are obscured when only positive results are published. We organize the discussion around four themes: the structural overhead boundary for speculative routing, the promise and limits of selective speculation, methodological pitfalls in batch optimization, and the broader implications for LLM routing research.

### 6.1 The Structural Overhead Boundary

The decisive finding from Experiment 1 is not the specific magnitude of the deficit ($-5.72$ pp) but the structural argument underlying it. In token-level speculative decoding \cite{leviathan2023fast, chen2023speculative}, the draft model's computation is effectively free because it is batched with the verifier on shared hardware. At the model level, this assumption fails: invoking Haiku costs real API dollars, and the judge adds further overhead. Every query pays at least $c_\text{Haiku} + c_\text{judge}$, and escalated queries pay this *on top of* the strong model's cost---a 24\% premium at the 1:5 cost ratio tested.

This overhead creates a break-even condition that can be stated precisely. Let $\alpha$ denote the fraction of queries the cascade correctly accepts at the cheap tier, and let $r = c_\text{strong} / (c_\text{cheap} + c_\text{judge})$ be the cost ratio. The cascade saves money over always-strong routing when $\alpha > 1 - 1/r$. At our parameterization ($r = 5.0/1.2 \approx 4.17$), the cascade requires $\alpha > 0.76$---i.e., the judge must correctly accept over three-quarters of queries at the cheap tier. The input-feature baseline achieves comparable savings by routing only $\sim$22\% of queries to Haiku, but with zero per-query overhead, its break-even condition is trivially satisfied.

This analysis generalizes beyond our specific simulation. For any API-billed multi-model cascade, the information advantage of observing output quality must be weighed against the structural overhead of always invoking the cheap model. The cascade becomes more favorable as the cost ratio increases (e.g., 1:10 or higher) or as judge quality improves (higher TPR at fixed FPR). Our results establish that at a 1:5 ratio with a moderate-quality judge, the overhead dominates---but they do not rule out the cascade at other operating points.

### 6.2 Selective Speculation: A Viable but Undecomposed Mechanism

Experiment 2 demonstrates that restricting speculation to an ambiguous query zone recovers the structural overhead problem. The +5.93 pp improvement over the pure input-feature baseline is directionally robust (all three seeds positive, 95\% CI excludes zero) but falls short of the pre-registered 8 pp threshold. The 95\% CI of [2.78, 9.08] straddles the threshold, leaving the magnitude genuinely uncertain at $n=3$.

Two validity concerns temper our interpretation. First, the improvement conflates two distinct mechanisms: the 3-zone triage itself (easy$\rightarrow$Haiku, hard$\rightarrow$Sonnet, ambiguous$\rightarrow$speculate) and the judge's accept/reject decision within the ambiguous zone. Without a triage-only ablation---routing ambiguous queries directly to Sonnet rather than speculating---we cannot attribute the gain. The triage is a trivial extension of the baseline (adding a second threshold); the judge is the novel component transplanted from speculative decoding. If triage accounts for most of the +5.93 pp, the contribution of output-quality signals is smaller than it appears.

Second, the ambiguous zone fraction varies from 23.3\% to 49.2\% across seeds, a 2$\times$ range driven by noise in the difficulty estimator interacting with fixed zone thresholds. This instability means the mechanism's practical benefit is highly sensitive to pre-screen calibration quality---a deployment concern that fixed-threshold routers, which have no such zone, avoid entirely.

Despite these caveats, the result is scientifically informative. It demonstrates that the failure of always-speculate (Experiment 1) is not a failure of output-quality routing *in general*, but of naive application without input-based pre-screening. The combination of input-feature triage with output-quality verification on the margin is a design pattern worth further investigation, consistent with the broader trend toward hybrid routing architectures that combine multiple signal types \cite{ong2024routellm, ding2024hybrid}.

### 6.3 Marginal Pricing in Multi-Tier Batch Optimization

Experiment 3's failure is instructive for a different reason: it exposes a subtle implementation pitfall in greedy knapsack formulations for multi-tier settings. The optimizer enumerates upgrade candidates from a common Haiku base (H$\rightarrow$S and H$\rightarrow$O), but after the first pass of H$\rightarrow$S upgrades moves most queries to Sonnet, the remaining H$\rightarrow$O candidates are effectively S$\rightarrow$O upgrades with a different marginal cost. The efficiency rankings invert: moderate-difficulty queries (where Sonnet already performs adequately) are ranked above hard queries (where Opus genuinely adds value), producing a pathological 75\% Opus allocation.

This is not a limitation of batch routing *per se* but of a specific greedy decomposition that fails to track current tier assignments. A correctly implemented batch router would either enumerate marginal upgrades from each query's current tier or use a proper LP/MILP formulation that jointly optimizes all assignments \cite{hu2024routerbench}. We report this as a methodological contribution: researchers implementing multi-tier batch optimization should verify that their marginal cost calculations reflect the current state of each query, not a fixed base tier.

The independent threshold router avoids this failure naturally: by routing each query based on its individual difficulty estimate, the threshold implicitly assigns hard queries to Opus and moderate queries to Sonnet without any inter-query coordination. This suggests that batch-level optimization may offer diminishing returns over well-tuned per-query thresholds when both use the same noisy predictor---the batch router's theoretical advantage (redistributing budget from low-delta to high-delta queries) may be small relative to the noise in the quality predictions.

### 6.4 Limitations

Our findings are bounded by several design choices that limit generalizability.

**Simulation fidelity.** All experiments operate on synthetic difficulty draws (Beta(2,3)) with sigmoid accuracy curves. Real LLM accuracy distributions are multimodal, exhibit correlated failures across models sharing training data, and include format-dependent errors that our binary correctness model cannot represent. The structural overhead argument (Section 6.1) is a mathematical identity independent of simulation fidelity, but all magnitude estimates ($-5.72$ pp, $+5.93$ pp, $-16.75$ pp) are simulation-specific and should not be cited as precise predictions for real deployments.

**Assumed judge quality.** The judge in Experiments 1--2 is parameterized along an assumed ROC curve with no empirical basis. HYP-002 proposed a regex + chain-of-thought-length judge for math problems, which on structured GSM8K could plausibly achieve TPR $\geq 0.90$ at FPR $\leq 0.03$---well above our simulation's best operating point. A stronger judge would improve the cascade's acceptance rate and potentially flip the sign of Experiment 1's result. Our findings are conditional on moderate judge quality.

**Statistical power.** Three seeds provide directional confidence but wide confidence intervals. Experiment 2's CI of [2.78, 9.08] cannot distinguish a moderate effect from a large one. For simulation experiments this cheap to run, 10+ seeds would substantially tighten estimates.

**Single cost structure.** Experiments 1--2 test only a 1:5 cost ratio; Experiment 3 tests 1:5:25. The break-even analysis in Section 6.1 shows that the cascade becomes more favorable at higher ratios---but we provide no empirical validation of this prediction. A cost-ratio sensitivity sweep is a natural extension.

**Missing ablations.** Experiment 2 lacks a triage-only ablation that would decompose the +5.93 pp into triage vs.\ judge contributions. This is the most important gap in our experimental design: without it, we cannot attribute the improvement to the novel component (output-quality verification).

**Untested hypothesis.** HYP-008 (batch routing) remains open rather than rejected, due to the implementation bug in EXP-003. The paper contributes the methodological finding but not a valid test of the underlying claim.

### 6.5 Implications for the Field

Three broader lessons emerge from this work.

First, **negative results in LLM routing deserve publication**. The routing literature is dominated by positive findings, each proposing a new architecture that outperforms baselines. Our pre-registered negative results on speculative cascade routing provide an honest counterpoint: a plausible, well-motivated approach that fails for identifiable structural reasons. The structural overhead analysis offers a reusable framework for evaluating future cascade proposals before running expensive experiments.

Second, **cross-domain transplants require careful cost-structure analysis**. Speculative decoding succeeds at the token level because the draft model's computation is amortized into shared hardware. Transplanting the same logic to API-billed model selection introduces a cost asymmetry that the original technique was not designed to handle. This cautionary finding applies to other cross-domain transfers in the LLM serving stack: techniques that work within a single model's inference pipeline may fail when applied across distinct, independently billed model endpoints.

Third, **multi-tier routing introduces combinatorial complexity that binary routing avoids**. The batch knapsack's marginal-pricing failure, the 3-zone triage's calibration sensitivity, and the general challenge of correctly pricing upgrade paths across 3+ tiers all point to a common theme: moving from binary to multi-tier routing is not simply "adding a model" but qualitatively changes the optimization landscape. Future work on multi-tier systems should explicitly verify marginal-cost calculations and test sensitivity to the number of tiers, as the failure modes we document are specific to the multi-tier setting and absent in binary routing.

### 6.6 Future Directions

Several extensions follow naturally from our findings. (1) **Real API validation**: running the selective speculation experiment on 100--500 actual GSM8K queries with Haiku and Sonnet API calls would ground the simulation-derived +5.93 pp in empirical reality. (2) **Triage-only ablation**: a straightforward experiment that routes ambiguous-zone queries directly to Sonnet (no judge) would decompose the contribution of output-quality signals. (3) **Judge architecture study**: replacing the parameterized judge with a real regex + chain-of-thought judge on math problems would test whether the break-even condition from Section 6.1 can be satisfied in practice. (4) **Corrected batch optimizer**: re-implementing the knapsack with proper marginal pricing (or an LP formulation) would provide a valid test of HYP-008. (5) **Cost-ratio sensitivity**: sweeping the Haiku:Sonnet ratio from 1:3 to 1:15 would map the boundary at which speculative cascade routing becomes competitive, connecting our theoretical break-even analysis to empirical operating points.
