---
{
  "id": "DRAFT-005",
  "type": "DraftSection",
  "created_at": "2026-04-27T05:59:12+00:00",
  "parent_ids": [
    "DRAFT-001",
    "IDEA-001",
    "HYP-002",
    "HYP-008",
    "EXP-001",
    "EXP-002",
    "EXP-003",
    "RES-001",
    "RES-002",
    "RES-003",
    "CRIT-016",
    "CRIT-017",
    "CRIT-018",
    "CRIT-019",
    "CRIT-020",
    "CRIT-021"
  ],
  "author": "paper-writer",
  "summary": "Method v1: simulation framework, three experiment designs (speculative cascade, selective speculation, batch knapsack), baselines, and evaluation protocol",
  "body_path": "thoughts/DRAFT-005.md",
  "section": "method",
  "version": 1,
  "citation_ids": [
    "CITE-006",
    "CITE-008",
    "CITE-009",
    "CITE-031",
    "CITE-023",
    "CITE-033"
  ],
  "text_path": "thoughts/DRAFT-005.md"
}
---


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
