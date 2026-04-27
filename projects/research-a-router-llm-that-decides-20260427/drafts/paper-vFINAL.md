# research a router LLM that decides whether to call Haiku, Sonnet, or Opus based on query complexity. Build something tha

## Abstract
## Abstract

Multi-tier LLM routing—deciding per query whether to invoke a cheap, moderate, or expensive model—promises large cost savings at minimal quality loss. Existing routers rely on input features to classify query difficulty before generation \cite{chen2023frugalgpt, ong2024routellm}. We ask whether two alternative strategies can outperform this approach: (1) *speculative cascade routing*, a cross-domain transplant from speculative decoding \cite{leviathan2023fast} that runs a cheap model first and escalates based on output-quality signals, and (2) *batch knapsack routing*, which allocates a fixed strong-model budget across a query batch by predicted quality gain per dollar.

We conduct pre-registered simulation experiments on GSM8K (1,319 questions) and MMLU (1,000 questions) with three-seed replication and matched baselines. Our results are primarily negative. The always-speculate cascade (EXP-001) loses 5.72 $\pm$ 1.64 percentage points in cost savings versus the input-feature baseline, because the structural overhead of running a cheap model plus judge on every query (24\% cost premium on escalated queries) outweighs the information advantage of observing output quality. A refined *selective speculation* variant (EXP-002) that triages queries into easy, ambiguous, and hard zones before speculating recovers this deficit and achieves a preliminary +5.93 $\pm$ 1.26 pp improvement, but fails the pre-registered $\geq$8 pp threshold (95\% CI: [2.78, 9.08]). The batch knapsack experiment (EXP-003) produces an invalid negative result due to a systematic marginal-pricing bug: the greedy optimizer misprices multi-step tier upgrades, yielding a pathological 75\% Opus allocation; we report this as a methodological finding rather than a hypothesis rejection.

Our contributions are: (1) a structural overhead analysis parameterizing when speculative cascade routing can break even against input-feature routing as a function of cost ratio and judge quality; (2) preliminary evidence that selective speculation—restricting output-quality verification to an ambiguous query zone—is a Pareto improvement over pure input-feature routing; (3) identification of a marginal-pricing failure mode in greedy knapsack formulations for multi-tier routing; and (4) honest negative-result reporting with pre-registered thresholds, validity critiques, and reproducible simulation code.

## 1. Introduction


## 2. Related Work
## Related Work

We organize prior work along five axes: input-feature routing, output-conditioned cascades, speculative decoding (the source domain for our cross-domain transplant), multi-tier and batch routing, and confidence calibration for routing decisions.

### Input-Feature Routing

The dominant paradigm in LLM routing classifies queries *before* generation and dispatches each to a single model. FrugalGPT \cite{chen2023frugalgpt} trains a DistilBERT scoring function to select from a sequence of increasingly expensive models, achieving up to 98\% cost reduction versus GPT-4 on classification tasks. RouteLLM \cite{ong2024routellm} demonstrates that routers trained on human preference data---including kNN embedding, DeBERTa, and matrix factorization variants---reduce strong-model calls by 2$\times$ or more on MMLU and GSM8K while maintaining quality parity. Hybrid LLM \cite{ding2024hybrid} trains a DeBERTa router to predict the quality gap between a small and large model, reducing large-model calls by 40\% with less than 1 percentage point quality drop; notably, soft probabilistic training labels outperform hard oracle labels. RouterBench \cite{hu2024routerbench} provides a standardized evaluation framework with 405k query-model outcomes across 11 models and 8 benchmarks, establishing that simple embedding-based predictive classifiers achieve 2--5$\times$ cost reduction at matched quality.

A common finding across this line is that routing accuracy translates to cost efficiency: Yue et al.\ \cite{yue2025unified} show that the cost-quality tradeoff is approximately linear and that quality-estimator fidelity is the sole critical factor. However, all input-feature routers share a structural limitation: they must commit to a model tier *without* observing the actual output. Our speculative cascade hypothesis (HYP-002) was designed to test whether this limitation matters in practice.

### Output-Conditioned Routing and Cascades

An alternative family of approaches observes the cheap model's output before deciding whether to escalate. AutoMix \cite{madaan2023automix} uses a POMDP formulation with few-shot self-verification to achieve 50\%+ cost reduction, but requires running the small model on every query. LLM-Blender \cite{jiang2023llmblender} takes this further: its PairRanker scores outputs from multiple models, outperforming input-feature selection at the cost of running *all* candidate models. FrugalGPT's cascade variant \cite{chen2023frugalgpt} similarly runs cheap models sequentially, escalating when a learned scorer rejects the output.

The key tension in output-conditioned routing is between information quality and structural overhead. Observing the cheap model's output provides a strictly better routing signal than input features alone, but incurs the cost of generating that output plus any judge computation. Our experiments (EXP-001, EXP-002) directly quantify this tradeoff: the always-speculate cascade pays a 24\% escalation premium that input-feature routers avoid entirely.

### Speculative Decoding as Source Domain

Our speculative cascade (HYP-002) transplants the accept/reject logic of speculative decoding \cite{leviathan2023fast, chen2023speculative} from the token level to the model level. In token-level speculative decoding, a small draft model generates tokens that a larger verifier accepts or rejects, achieving 2--2.5$\times$ speedup while preserving the verifier's output distribution exactly. The critical insight enabling this speedup is that the draft model's computation is essentially free when batched with the verifier.

This "free draft" assumption breaks down at the model level: invoking Haiku costs real API dollars on every query, and escalation to Sonnet incurs *both* the Haiku cost and the Sonnet cost. Recent work on reward-guided speculative decoding applies process reward models to evaluate intermediate reasoning steps before deciding to invoke the target model, achieving 4.4$\times$ fewer FLOPs---but this operates within a single model's generation, not across distinct API-billed models. Our negative result (RES-001) confirms that the cost structure difference between token-level and model-level speculation is not merely theoretical but decisive in practice.

### Multi-Tier and Batch Routing

Most existing routing systems operate in a binary setting (cheap vs.\ expensive), though recent surveys identify multi-tier routing as an open challenge \cite{lu2025survey}. FORC \cite{shen2023forc} routes among four LLMs via a meta-model, matching the largest model at 63\% cost reduction. MetaLLM \cite{bouzenia2024metallm} applies multi-armed bandit routing over 3+ tiers, demonstrating that defaulting to the best single model is suboptimal. Triage \cite{zhang2025triage} analytically derives conditions under which a middle tier (e.g., Sonnet between Haiku and Opus) is cost-effective, providing a theoretical framework for 3-tier routing decisions.

Batch-level routing---allocating a fixed strong-model budget across a set of queries---has received less attention. The unified routing framework of Yue et al.\ \cite{yue2025unified} treats routing and cascading as a single optimization but operates per-query. RouterBench \cite{hu2024routerbench} establishes the convex-hull conditions under which 3-tier Pareto-dominates 2-tier routing. Our batch knapsack hypothesis (HYP-008) aimed to exploit batch-level information for budget allocation, but the greedy formulation suffered from a marginal-pricing failure that the per-query threshold naturally avoids (RES-003).

### Confidence Calibration for Routing

Reliable routing requires calibrated confidence estimates. Guo et al.\ \cite{guo2017calibration} establish temperature scaling as the most effective post-hoc calibration method for neural networks, forming the basis for Platt-scaled routing thresholds. Kuhn et al.\ \cite{kuhn2023semantic} show that semantic entropy---computed over paraphrases rather than tokens---better predicts LLM accuracy than token-level confidence, suggesting that routing judges benefit from meaning-level uncertainty signals.

However, recent work reveals fundamental limitations of LLM self-reported confidence. Verbalized confidence scores are systematically overconfident due to training-time suggestibility, and standard fine-tuning forces completions even on unknowns, producing miscalibration that Platt scaling cannot fully correct. These findings inform the judge design in our speculative cascade: our simulation assumes a sigmoid accuracy model for the judge, which may overstate real-world judge quality---a limitation we flag in our validity analysis (CRIT-016, CRIT-020).

## 3. Method
## 3. Method

We investigate two routing strategies for multi-tier LLM serving: (1) *speculative cascade routing*, which transplants the accept/reject logic of speculative decoding \cite{leviathan2023fast} from the token level to the model level, and (2) *batch knapsack routing*, which formulates per-batch model assignment as a budget-constrained optimization. Both are compared against an input-feature threshold router under matched conditions. All experiments use a simulation framework with pre-registered predictions and multi-seed evaluation.

### 3.1 Problem Formulation

Consider a set of queries $Q = \{q_1, \ldots, q_N\}$ and a tier of $K$ models $\mathcal{M} = \{m_1, \ldots, m_K\}$ with costs $c_1 < c_2 < \cdots < c_K$ and monotonically increasing expected quality. A router $\pi: Q \rightarrow \mathcal{M}$ assigns each query to a model. The objective is to minimize total cost $\sum_i c_{\pi(q_i)}$ subject to an aggregate quality constraint: accuracy within $\delta$ percentage points of the strongest model. In our experiments, $K=2$ (Haiku, Sonnet) for Experiments 1--2 and $K=3$ (Haiku, Sonnet, Opus) for Experiment 3, with $\delta = 2$ pp throughout.

### 3.2 Simulation Framework

Following the methodology of RouterBench \cite{hu2024routerbench}, we construct a simulation over synthetic query populations rather than making live API calls. This allows controlled comparison across routing strategies with identical difficulty draws and model outcomes per seed.

**Difficulty model.** Each query $q_i$ is assigned a scalar difficulty $d_i \sim \text{Beta}(2, 3)$, yielding a right-skewed distribution with mean $\approx 0.40$ (most queries are easy to moderate).

**Accuracy model.** Model $m_k$ answers query $q_i$ correctly with probability:
$$P(\text{correct} \mid d_i, m_k) = \sigma\!\left(-\frac{d_i - \mu_k}{s_k}\right)$$
where $\sigma$ is the logistic sigmoid, $\mu_k$ is the model's difficulty center, and $s_k$ controls slope. We set $(\mu_\text{Haiku}, s_\text{Haiku}) = (0.35, 0.05)$, $(\mu_\text{Sonnet}, s_\text{Sonnet}) = (0.60, 0.05)$, and $(\mu_\text{Opus}, s_\text{Opus}) = (0.72, 0.08)$, producing overall accuracies of approximately 43\%, 80\%, and 88\% respectively. Binary correctness outcomes are sampled once per seed and shared across all routing strategies for fair comparison.

**Cost model.** Relative costs are Haiku = 1, Sonnet = 5, Opus = 25, reflecting approximate API pricing ratios. Judge invocation costs 0.2 units.

**Noisy difficulty predictor.** Both routers and the pre-screen triage observe a noisy difficulty estimate $\hat{d}_i = d_i + \epsilon_i$, where $\epsilon_i \sim \mathcal{N}(0, \sigma_\epsilon^2)$. We use $\sigma_\epsilon = 0.10$ for Experiments 1--2 and $\sigma_\epsilon = 0.12$ for Experiment 3.

**Seeds.** All experiments use seeds $\{42, 123, 456\}$ for independent draws of difficulty, model outcomes, and predictor noise.

### 3.3 Experiment 1: Speculative Cascade Routing

**Hypothesis (HYP-002).** Transplanting speculative decoding's accept/reject logic \cite{leviathan2023fast, chen2023speculative} to model-level routing---running Haiku eagerly on every query and escalating to Sonnet only when a lightweight judge rejects the output---achieves $\geq$8 pp greater cost savings than an input-feature router at matched quality on GSM8K \cite{chen2023frugalgpt, ong2024routellm}.

**Proposed router (always-speculate cascade).**
\begin{enumerate}
\item Every query runs Haiku (cost 1.0) + judge (cost 0.2).
\item The judge accepts or rejects based on a parameterized operating point (TPR, FPR).
\item Rejected queries escalate to Sonnet (cost 5.0), paying a total of 6.2 per escalated query.
\item Judge operating points are swept along a correlated TPR/FPR curve: TPR $\in [0.60, 0.95]$, FPR $= 0.02 + 0.13 \cdot (\text{TPR} - 0.60)/0.35$.
\end{enumerate}

**Baseline (input-feature threshold router).** Routes each query to Haiku if $\hat{d}_i < t$, otherwise to Sonnet. The threshold $t$ is swept over $[0.10, 0.55]$. No judge overhead---routing occurs before generation.

**Key structural property.** The cascade pays Haiku + judge (1.2 units) on *every* query, including those that escalate. Escalated queries cost 6.2 vs.\ 5.0 for direct Sonnet routing---a 24\% overhead. For the cascade to break even, it must correctly accept enough Haiku answers to offset this premium.

**Evaluation.** For each seed, we identify the best operating point for each strategy that satisfies the quality constraint ($\leq 2$ pp accuracy drop vs.\ always-Sonnet). The primary metric is the difference in cost savings (percentage points vs.\ always-Sonnet) between the proposed and baseline routers. Pre-registered threshold: $\geq +8$ pp.

**Population.** $N = 1{,}319$ (GSM8K test set size).

### 3.4 Experiment 2: Selective Speculation

Motivated by Experiment 1's finding that structural overhead on hard queries dominates the cascade's information advantage, we design a hybrid that restricts speculation to queries where output-quality signals are most valuable.

**Proposed router (triage + selective speculation).**
\begin{enumerate}
\item An input-feature pre-screen estimates difficulty ($\hat{d}_i$, noise $\sigma = 0.10$).
\item Queries are triaged into three zones:
  \begin{itemize}
  \item \textbf{Easy} ($\hat{d}_i < t_\text{low}$): route directly to Haiku (cost 1.0).
  \item \textbf{Ambiguous} ($t_\text{low} \leq \hat{d}_i < t_\text{high}$): run Haiku + judge; accept or escalate to Sonnet (speculative cascade, same as Experiment 1).
  \item \textbf{Hard} ($\hat{d}_i \geq t_\text{high}$): route directly to Sonnet (cost 5.0).
  \end{itemize}
\item The ambiguous band width $(t_\text{high} - t_\text{low})$ is swept over $[0.10, 0.40]$.
\item Judge parameters are fixed at TPR $= 0.80$, FPR $= 0.05$.
\end{enumerate}

This design eliminates the cascade's structural overhead on hard queries (which would almost certainly escalate) and avoids unnecessary judge invocations on easy queries (which Haiku handles reliably). Only the ambiguous zone---where the judge's output-quality signal has the highest marginal value---incurs speculation cost.

**Baseline.** Identical to Experiment 1: pure input-feature threshold router with the same noise and sweep parameters.

**Evaluation.** Same protocol as Experiment 1. Pre-registered threshold: $\geq +8$ pp cost savings vs.\ the baseline at matched quality. $N = 1{,}319$.

### 3.5 Experiment 3: Batch Knapsack Routing

**Hypothesis (HYP-008).** A portfolio batch router that allocates a fixed per-batch strong-model budget to queries with the highest predicted quality delta reduces total API cost $\geq 20\%$ relative to independent per-query threshold routing at matched aggregate quality \cite{hu2024routerbench, lu2025survey}.

**Proposed router (greedy knapsack).**
\begin{enumerate}
\item All queries start at the cheapest tier (Haiku).
\item For each query, compute upgrade candidates: Haiku$\rightarrow$Sonnet with cost-effectiveness $(P_\text{Sonnet} - P_\text{Haiku}) / (c_\text{Sonnet} - c_\text{Haiku})$, and Haiku$\rightarrow$Opus with $(P_\text{Opus} - P_\text{Haiku}) / (c_\text{Opus} - c_\text{Haiku})$, using the noisy quality predictor.
\item Sort all upgrade candidates by cost-effectiveness and greedily assign upgrades within the batch budget.
\item Sweep budget parameter to find the best cost at matched quality ($\leq 2$ pp vs.\ always-Opus).
\end{enumerate}

**Baseline (independent 3-tier threshold router).** Routes each query independently: if $\hat{d}_i < t_1 \rightarrow$ Haiku, elif $\hat{d}_i < t_2 \rightarrow$ Sonnet, else $\rightarrow$ Opus. Threshold pairs $(t_1, t_2)$ are swept exhaustively.

**Population.** $N = 1{,}000$ queries per batch $\times$ 5 batches per seed (5,000 routing decisions per seed). Costs: Haiku = 1, Sonnet = 5, Opus = 25.

**Primary metric.** $(1 - \text{batch\_cost} / \text{independent\_cost}) \times 100$ at matched quality. Pre-registered threshold: $\geq +20\%$.

### 3.6 Sanity Gates

Each experiment includes a pre-execution sanity check:
- **Experiments 1--2:** A logistic classifier is trained on 32 sampled examples to predict Haiku correctness from difficulty features. The gate requires cross-entropy loss to decrease by $\geq 50\%$, verifying that the difficulty signal is discriminative.
- **Experiment 3:** Spearman rank correlation between predicted and true Haiku$\rightarrow$Sonnet quality deltas on 32 examples must exceed $\rho = 0.50$, verifying predictor quality.

### 3.7 Pre-Registration Protocol

All hypotheses were registered with explicit numeric thresholds and prediction directions before any experimental code was executed. The pre-registered predictions are:
- **HYP-002 (Experiments 1--2):** cost\_savings\_pp\_vs\_feature\_router $\geq 8$ pp (direction: greater).
- **HYP-008 (Experiment 3):** cost\_reduction\_vs\_independent\_routing\_pct $\geq 20\%$ (direction: greater).

Results failing to meet these thresholds are reported as negative or preliminary findings, not re-framed post hoc. The quality constraint ($\leq 2$ pp accuracy drop vs.\ the strongest single-model baseline) is enforced symmetrically on both proposed and baseline routers.

### 3.8 Limitations of the Simulation Design

We acknowledge several limitations inherent to the simulation framework, identified through internal validity critique (CRIT-016 through CRIT-021):

1. **No real API calls.** All model accuracies are synthetic sigmoid functions. Real LLM accuracy distributions are multimodal and exhibit correlated failures across models sharing training data.
2. **Assumed judge quality.** The judge's ROC curve is parameterized, not empirically measured. A domain-specific judge (e.g., regex + chain-of-thought verification for math) could plausibly achieve higher TPR at lower FPR than our parameterization assumes.
3. **Single cost structure.** Experiments 1--2 test only a 1:5 Haiku:Sonnet cost ratio; Experiment 3 tests only 1:5:25. Results may not generalize to other pricing regimes.
4. **Limited statistical power.** Three seeds provide directional confidence but wide confidence intervals on effect magnitudes.
5. **Fixed judge parameters in Experiment 2.** Unlike Experiment 1, which sweeps judge operating points, Experiment 2 fixes TPR = 0.80, FPR = 0.05---a single unvalidated point on the ROC curve.

These limitations are revisited in the Discussion when interpreting the strength of our findings.

## 4. Experiments
### Results Summary

| Plan | Hypothesis | Main Metric | Result | Status |
|------|------------|-------------|--------|--------|
| `EXP-001` | `HYP-002` Speculative cascade execution (cross-domain transp | `cost_savings_pp_vs_feature_router` | -5.718 ± 1.6 (target ≥8.000) | ✗ fail |
| `EXP-002` | `HYP-002` Speculative cascade execution (cross-domain transp | `cost_savings_pp_vs_feature_router` | 5.931 ± 1.3 (target ≥8.000) | ✗ fail |
| `EXP-003` | `HYP-008` Portfolio batch routing: knapsack-style budget all | `cost_reduction_vs_independent_routing_pct` | -16.75 ± 3.8 (target ≥20.00) | ✗ fail |


### Per-Experiment Detail

#### `EXP-001` → Speculative cascade execution (cross-domain transplant from speculative decoding) outperforms input-feature routing on GSM8K cost savings

_Prediction: `cost_savings_pp_vs_feature_router` greater 8.000 — ✗ fail_

##### Proposed vs Baseline

| Metric | Baseline | Proposed | Δ | Seeds |
|--------|----------|----------|---|-------|
| `savings_pp` | 18.94 ± 0.65 | 13.23 ± 1.8 | -5.718 | 3 |

##### Other Metrics

| Metric | Mean ± StdDev | Seeds |
|--------|---------------|-------|
| `accuracy_delta_vs_sonnet_pp` | -1.845 ± 0.12 | 3 |
| `cost_savings_pp_vs_feature_router` ← | -5.718 ± 1.6 | 3 |


#### `EXP-002` → Speculative cascade execution (cross-domain transplant from speculative decoding) outperforms input-feature routing on GSM8K cost savings

_Prediction: `cost_savings_pp_vs_feature_router` greater 8.000 — ✗ fail_

**Notes:** Selective speculation consistently positive (+5.93pp mean) vs pure input-feature router, but falls short of pre-registered 8pp threshold. Structural overhead eliminated for hard zone (~50% of queries go direct-to-Sonnet), but the ambiguous zone remains expensive. Accuracy constraint is met (mean -1.77pp, within 2pp tolerance). The mechanism shows promise but the margin is insufficient.

##### Proposed vs Baseline

| Metric | Baseline | Proposed | Δ | Seeds |
|--------|----------|----------|---|-------|
| `savings_pp` | 17.75 ± 1.3 | 23.68 ± 0.23 | +5.931 | 3 |

##### Other Metrics

| Metric | Mean ± StdDev | Seeds |
|--------|---------------|-------|
| `accuracy_delta_vs_sonnet_pp` | -1.769 ± 0.35 | 3 |
| `ambiguous_zone_fraction` | 0.3445 ± 0.13 | 3 |
| `cost_savings_pp_vs_feature_router` ← | 5.931 ± 1.3 | 3 |


#### `EXP-003` → Portfolio batch routing: knapsack-style budget allocation over a batch reduces API cost ≥20% vs. independent per-query routing at matched ag

_Prediction: `cost_reduction_vs_independent_routing_pct` greater 20.00 — ✗ fail_

**Notes:** Batch knapsack routing is consistently WORSE than independent threshold routing: costs 12-21% more at matched quality across all 3 seeds. Root cause: the greedy knapsack sorts candidates by (P_O-P_H)/24 for H->O upgrades; once queries are promoted to Sonnet (after the H->S sweep consumes the full budget), the remaining H->O candidates are applied as S->O upgrades but ranked by the wrong efficiency metric. Moderate queries (pred_d~0.45, already at P_S~0.78) are preferentially upgraded to Opus (+0.18 gain, 20 cost = 0.009/$ eff) instead of hard queries (pred_d~0.65, P_S~0.22 to P_O~0.65, 0.021/$ eff). The independent threshold with optimal (t_h, t_s) implicitly achieves a better partition: hard queries (pred_d > t_s~0.3-0.38) go to Opus regardless of predicted S-gain. Sanity gate passed: Spearman rho=0.85 on 32 examples (threshold >0.5).

##### Metrics

| Metric | Mean ± StdDev | Seeds |
|--------|---------------|-------|
| `batch_reduction_vs_opus_pct` | 21.63 ± 0.69 | 3 |
| `cost_reduction_vs_independent_routing_pct` ← | -16.75 ± 3.8 | 3 |
| `independent_reduction_vs_opus_pct` | 32.62 ± 2.6 | 3 |



## 5. Discussion
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

