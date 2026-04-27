---
{
  "id": "DRAFT-005",
  "type": "DraftSection",
  "created_at": "2026-04-27T01:42:16+00:00",
  "parent_ids": [
    "DRAFT-001",
    "DRAFT-003",
    "IDEA-001",
    "HYP-001",
    "HYP-002",
    "HYP-006",
    "HYP-007",
    "EXP-001",
    "EXP-002",
    "EXP-003",
    "EXP-004",
    "CRIT-008",
    "CRIT-009",
    "CRIT-010",
    "CRIT-011"
  ],
  "author": "paper-writer",
  "summary": "Method v1: problem formulation, four pre-registered routing strategies, experimental protocols, baselines and metrics",
  "body_path": "thoughts/DRAFT-005.md",
  "section": "method",
  "version": 1,
  "citation_ids": [
    "CITE-001",
    "CITE-006",
    "CITE-007",
    "CITE-009",
    "CITE-016",
    "CITE-021",
    "CITE-022",
    "CITE-023",
    "CITE-024",
    "CITE-025",
    "CITE-026",
    "CITE-027",
    "CITE-029",
    "CITE-030"
  ],
  "text_path": "thoughts/DRAFT-005.md"
}
---

\paragraph{Pre-registered prediction (HYP-001).} The entropy router achieves quality\_at\_budget\_normalized $\geq 0.05$ above the text-feature baseline (direction: greater).

\paragraph{Evaluation.} Primary metric: \emph{quality\_at\_budget\_normalized}---the mean of (accuracy at budget $b$) / (normalized cost at $b$) across five budget points corresponding to escalation rates of 10\%, 25\%, 50\%, 75\%, and 100\%. Three seeds; mean $\pm$ standard deviation.

### 3.4 Strategy 3: Decompose-Then-Route

\paragraph{Motivation.} Every router in the literature treats the incoming query as an atomic unit \cite{ong2024routellm, chen2023frugalgpt, hu2024routerbench}. Yet complex multi-hop queries contain sub-problems of heterogeneous difficulty. Routing the entire query to the strongest model because one sub-problem is hard wastes cost on the easy sub-problems. We transplant query decomposition from the question-answering literature into the routing setting.

\paragraph{Pipeline.} The proposed system has four stages:
\begin{enumerate}
\item \textbf{Decompose}: a Haiku-tier model (Qwen2.5-0.5B-Instruct) splits the multi-hop question into two atomic sub-questions via few-shot prompting.
\item \textbf{Route}: a lightweight BERT-based complexity classifier assigns each sub-question to one of three tiers (Haiku/Sonnet/Opus).
\item \textbf{Answer}: each sub-question is sent to its assigned tier model.
\item \textbf{Merge}: a Haiku-tier model synthesizes a final answer from the sub-answers.
\end{enumerate}

The decomposer, router, and merger costs are all counted in the total budget.

\paragraph{Simulated cost model.} Three local proxy tiers: Qwen2.5-0.5B (Haiku, \$0.25/Mtok), Qwen2.5-1.5B (Sonnet, \$3.00/Mtok), Qwen2.5-3B (Opus, \$15.00/Mtok). Cost = (input + output tokens) $\times$ tier rate per call, summed across all pipeline stages.

\paragraph{Baseline.} Always-Opus: every question is routed to the 3B model. A second baseline variant applies the same BERT router to the whole query (without decomposition) to isolate the effect of decomposition granularity.

\paragraph{Dataset.} HotpotQA distractor development set, first 500 examples. HotpotQA is structurally 2-hop: each question requires chaining two supporting facts, making it a natural testbed for decomposition. The BERT router is trained on a separate 200-example split.

\paragraph{Pre-registered prediction (HYP-007).} Decompose-then-route reduces total cost by $\geq 15\%$ compared to whole-query Opus routing, at matched F1 accuracy (within 1pp tolerance).

\paragraph{Evaluation.} Primary metric: \emph{cost\_reduction\_percent\_at\_matched\_f1}---the percentage cost reduction when the proposed system's F1 is within 1pp of the baseline's F1. Secondary: raw F1 and raw cost reduction. Three seeds; mean $\pm$ standard deviation.

### 3.5 Strategy 4: Online Contextual-Bandit Routing

\paragraph{Motivation.} All surveyed routers are trained offline on a fixed dataset and deployed without adaptation. When the query distribution shifts---new user cohorts, new task domains, API capability changes---static routers degrade with no recovery mechanism. We transplant contextual Thompson Sampling from the multi-armed bandit literature into LLM routing \cite{ong2024routellm, hu2024routerbench}, maintaining per-arm posteriors that update after each observed quality-cost outcome.

\paragraph{Architecture.} Queries are encoded by a frozen all-MiniLM-L6-v2 encoder ($d=384$, projected to $d=32$ via PCA for computational tractability). The bandit maintains three arms (Haiku/Sonnet/Opus), each parameterized by a linear reward model with Gaussian posterior. At each query, Thompson Sampling draws weight vectors from the posteriors and selects the arm with the highest predicted reward. After the selected model responds, the reward $r = Q - \alpha \cdot (c / c_\text{max})$ (with quality penalty coefficient $\alpha = 0.3$) is observed and the arm's posterior is updated via rank-one covariance updates.

\paragraph{Baseline.} A static logistic-regression router trained on 2{,}000 in-distribution (ID) examples with calibrated labels. The static router is frozen at deployment.

\paragraph{Simulated environment.} Rather than calling live APIs, we simulate quality outcomes from calibrated Beta distributions fitted to published RouterBench numbers \cite{hu2024routerbench}: Haiku quality $\sim \text{Beta}(\alpha_h, \beta_h)$ with mean $\approx 0.55$ in-distribution and $\approx 0.35$ out-of-distribution, Sonnet $\approx 0.72 / 0.65$, Opus $\approx 0.88 / 0.85$. Cost model: Haiku = 1, Sonnet = 5, Opus = 15 (normalized units).

\paragraph{Distribution-shift protocol.} Phase 1 (warm-up): 2{,}000 general-knowledge queries from MMLU validation (ID). Phase 2 (evaluation): 500 queries from HumanEval docstrings and GSM8K (code + math, OOD). Online methods continue updating during Phase 2; the static baseline is frozen.

\paragraph{Additional online baselines.} To address the concern that any online method might outperform a static router \cite{hu2024routerbench}, we include two additional online comparators: (i) epsilon-greedy ($\varepsilon = 0.1$) with per-cluster empirical reward tracking ($k=20$ clusters), and (ii) a sliding-window baseline that picks the arm with the highest mean reward in the last $W=50$ queries per cluster.

\paragraph{Pre-registered prediction (HYP-006).} Thompson Sampling achieves quality\_cost\_auc\_ood $\geq 0.08$ above the static baseline (direction: greater) after 500 OOD queries.

\paragraph{Evaluation.} Primary metric: \emph{quality\_cost\_auc\_ood}---area under the quality-vs-cost curve across cost thresholds $\{0, 0.2, 0.4, 0.6, 0.8, 1.0\}$ on the 500 OOD queries. Secondary: ID AUC (sanity check), cumulative regret, and average OOD cost. Five seeds (42, 123, 7, 2024, 99); mean $\pm$ standard deviation.

### 3.6 Shared Experimental Protocol

\paragraph{Pre-registration.} All four hypotheses were registered before any code was run, with explicit metric names, numeric thresholds, and directionality. No post-hoc metric changes are applied: a hypothesis passes only if the pre-registered primary metric exceeds the pre-registered threshold in the pre-registered direction.

\paragraph{Sanity gate.} Before each main run, a sanity check trains on 32 examples for up to 60 seconds and verifies that the training loss decreases by $\geq 50\%$. This catches implementation bugs before committing compute.

\paragraph{Seeds and reporting.} Every experiment uses at least three random seeds to assess variance. Results are reported as mean $\pm$ standard deviation. We note that three seeds provide only a coarse estimate of the sampling distribution; we discuss statistical power limitations in Section 5.

\paragraph{Reproducibility.} Each experiment directory contains the full runnable code, per-seed logs, a canonical \texttt{result.json}, and an executable \texttt{repro.sh} script that recreates the run from scratch (including seed, environment, and command).
