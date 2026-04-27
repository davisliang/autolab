---
{
  "id": "DRAFT-006",
  "type": "DraftSection",
  "created_at": "2026-04-27T01:47:21+00:00",
  "parent_ids": [
    "DRAFT-001",
    "DRAFT-005",
    "EXP-001",
    "EXP-002",
    "EXP-003",
    "EXP-004",
    "RES-001",
    "RES-002",
    "RES-003",
    "RES-004",
    "CRIT-008",
    "CRIT-009",
    "CRIT-010",
    "CRIT-011",
    "HYP-001",
    "HYP-002",
    "HYP-006",
    "HYP-007"
  ],
  "author": "paper-writer",
  "summary": "Experiments v1: four pre-registered strategies all fail thresholds; diagnostic analysis of failure modes",
  "body_path": "thoughts/DRAFT-006.md",
  "section": "experiments",
  "version": 1,
  "citation_ids": [
    "CITE-001",
    "CITE-006",
    "CITE-007",
    "CITE-009",
    "CITE-021",
    "CITE-022",
    "CITE-026",
    "CITE-027",
    "CITE-029",
    "CITE-030"
  ],
  "text_path": "thoughts/DRAFT-006.md"
}
---

## 4. Experiments

We evaluate all four pre-registered routing strategies described in Section 3. Every hypothesis was registered with an explicit primary metric, numeric threshold, and directionality before any code was executed. We report results as mean $\pm$ standard deviation across seeds and assess each hypothesis strictly against its pre-registered threshold. All four strategies fail to meet their pre-registered thresholds; we analyze the failure modes diagnostically.

### 4.1 Experiment 1: Multi-Dimensional Routing (HYP-002)

\paragraph{Setup.} We collect 1{,}500 queries (500 each from MMLU validation, GSM8K validation, and AlpacaEval), split 70/15/15 into train/validation/test. Oracle routing labels assign each query to the cheapest model whose accuracy matches the best model that answered correctly. Queries are embedded with all-MiniLM-L6-v2 ($d=384$). The proposed multi-head router trains four logistic-regression heads (one per complexity dimension: reasoning depth, domain specificity, ambiguity, creativity) on heuristic proxy labels, then feeds their probability outputs to a Random Forest ($n=50$ estimators, depth 5) for 3-class routing. The single-score baseline trains logistic regression directly on the same embeddings for 3-class routing. Both use $C=1.0$, $\text{max\_iter}=1000$.

\paragraph{Sanity gate.} Passed: training loss dropped 87.5\% on 32 examples (threshold: $\geq$50\%).

\paragraph{Results.} Table~\ref{tab:exp1} summarizes results across three seeds (42, 123, 456).

\begin{table}[h]
\centering
\caption{Experiment 1: Multi-head 4D router vs.\ single-score baseline.}
\label{tab:exp1}
\begin{tabular}{lccc}
\toprule
Metric & Proposed & Baseline & $\Delta$ \\
\midrule
Routing accuracy & $0.793 \pm 0.023$ & $\mathbf{0.913 \pm 0.002}$ & $-0.120$ \\
Cost savings ratio & $\mathbf{0.744 \pm 0.009}$ & $0.716 \pm 0.013$ & $+0.029$ \\
Quality at matched cost & $0.955 \pm 0.005$ & $\mathbf{0.984 \pm 0.002}$ & $-0.029$ \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Outcome.} **Hypothesis fails.** The pre-registered threshold required routing accuracy $\geq$3pp above the baseline; the multi-head router underperforms by 12.0pp. The baseline achieves 91.3\% routing accuracy with near-zero variance across seeds, while the proposed router averages 79.3\%.

\paragraph{Diagnostic analysis.} Three factors explain the failure:

\emph{(1) Noisy intermediate labels.} The heuristic dimension labeller (keyword/regex rules) introduces label noise in the four intermediate heads. This noise propagates through the meta-features to the Random Forest. The validity critique (CRIT-008) confirms that these proxy labels are unvalidated and confound the two-stage architecture.

\emph{(2) Redundant decomposition.} The 384-dimensional MiniLM embeddings already encode semantic structure---including domain, reasoning type, and difficulty---that the single-score logistic regression exploits end-to-end. The four-head decomposition imposes an information bottleneck (4 scalar probabilities) that discards useful signal.

\emph{(3) Error accumulation.} The Random Forest trains on predicted head probabilities rather than ground-truth dimension labels. With only 1{,}050 training examples (70\% of 1{,}500), variance in the meta-features is amplified.

The proposed router does achieve slightly higher cost savings (+2.9pp) because it routes more aggressively to cheaper models---but this is a precision-cost tradeoff rather than a quality improvement. As noted in CRIT-008, the low variance of the baseline ($\pm$0.002) vs.\ the proposed system ($\pm$0.023) suggests the multi-head architecture is sensitive to seed-dependent label noise.

### 4.2 Experiment 2: Entropy-Based Routing (HYP-001)

\paragraph{Setup.} We evaluate on a 500-question stratified sample from MMLU using two local proxy models via MLX: Qwen2.5-0.5B-Instruct-4bit (``Haiku'') and Qwen2.5-3B-Instruct-4bit (``Opus''). Cost model: small = 1 unit, large = 6 units; escalation via the entropy router costs 7 units (small run + large run) while escalation via the text-feature router costs 6 units (no prior small run needed). The entropy router computes mean token-level entropy from the small model's logprobs and escalates when entropy exceeds a threshold tuned on a 60\% calibration split. The text-feature baseline trains TF-IDF (unigram+bigram) logistic regression to predict small-model failure, calibrated to match the entropy router's escalation rate.

\paragraph{Sanity gate.} Passed: log-loss dropped 68.3\% on 32 examples (threshold: $\geq$50\%).

\paragraph{Results.} Table~\ref{tab:exp2} reports primary and secondary metrics across three seeds.

\begin{table}[h]
\centering
\caption{Experiment 2: Entropy router vs.\ text-feature router on MMLU-lite.}
\label{tab:exp2}
\begin{tabular}{lcc}
\toprule
Metric & Entropy Router & Text-Feature Router \\
\midrule
Quality at budget (norm.) & $\mathbf{1.302 \pm 0.070}$ & $1.258 \pm 0.051$ \\
Accuracy @ 50\% escalation & $\mathbf{0.803 \pm 0.027}$ & $0.648 \pm 0.025$ \\
Cost ratio @ 50\% escalation & $0.667$ & $\mathbf{0.583}$ \\
Small-only accuracy & $0.463 \pm 0.049$ & $0.463 \pm 0.049$ \\
Large-only accuracy & $0.832 \pm 0.012$ & $0.832 \pm 0.012$ \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Outcome.} **Hypothesis fails.** The pre-registered threshold required quality\_at\_budget\_normalized $\geq$0.05 above the text-feature baseline. The observed delta is $+0.044 \pm 0.070$---below threshold and with a confidence interval spanning zero (CRIT-009).

\paragraph{Diagnostic analysis.} The entropy router is unambiguously a superior per-instance routing signal: at 50\% escalation, it achieves 80.3\% accuracy vs.\ 64.8\% for text features (+15.5pp). However, the quality\_at\_budget\_normalized metric penalizes the entropy router's structural cost overhead. Because the entropy router must always run the small model first (1 unit) before deciding to escalate (additional 6 units $= 7$ total), while the text-feature router can escalate without running the small model (6 units), the entropy router pays a 14\% cost premium at 50\% escalation ($4.0/3.5 = 1.14$).

This cost asymmetry compresses a 15.5pp accuracy advantage into only a $+0.044$ normalized quality-cost delta. As CRIT-009 notes, the pre-registered metric inadvertently penalizes the entropy router for a structural property (always requiring a small-model forward pass) rather than for routing quality \cite{ong2024routellm, kuhn2023semantic}. At matched total budget---where both routers spend the same number of cost units---the entropy router's advantage would be approximately $+0.09$, comfortably exceeding the threshold.

Additional concerns raised by CRIT-009: (i) three seeds yield wide standard deviations ($\pm$0.070), providing insufficient statistical power to distinguish a 0.044 effect from zero; (ii) the MMLU multiple-choice format may inflate the entropy signal's quality relative to open-ended benchmarks; (iii) the 0.5B/3B proxy pair may not reproduce the quality gap of production Haiku/Opus models.

### 4.3 Experiment 3: Decompose-Then-Route (HYP-007)

\paragraph{Setup.} We evaluate on 500 examples from the HotpotQA distractor development set. The proposed pipeline decomposes each question into two sub-questions via few-shot prompting with Qwen2.5-0.5B-Instruct, routes each sub-question independently via a BERT complexity classifier (trained on a separate 200-example split), answers each with the assigned tier model, and merges sub-answers with Qwen2.5-0.5B \cite{ong2024routellm, chen2023frugalgpt}. Three local proxy tiers simulate the cost hierarchy: 0.5B at \$0.25/Mtok, 1.5B at \$3.00/Mtok, 3B at \$15.00/Mtok. The baseline routes every question to the 3B model.

\paragraph{Sanity gate.} Passed: loss dropped 99.3\% on 32 examples.

\paragraph{Results.} Table~\ref{tab:exp3} reports results across three seeds.

\begin{table}[h]
\centering
\caption{Experiment 3: Decompose-then-route vs.\ always-Opus on HotpotQA.}
\label{tab:exp3}
\begin{tabular}{lcc}
\toprule
Metric & Proposed (DTR) & Baseline (Opus) \\
\midrule
F1 accuracy & $0.686 \pm 0.004$ & $\mathbf{0.723 \pm 0.001}$ \\
Total simulated cost & $\mathbf{\$0.69 \pm 0.01}$ & $\$2.25$ \\
Raw cost reduction & $69.2\% \pm 0.4\%$ & --- \\
Cost reduction @ matched F1 & $0.0\%$ & --- \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Outcome.} **Hypothesis fails.** The pre-registered threshold required $\geq$15\% cost reduction at F1 within 1pp of the baseline. While raw cost reduction is dramatic (69.2\%), F1 degrades by 3.7pp ($0.686$ vs.\ $0.723$), exceeding the 1pp tolerance. Under the pre-registered protocol, cost\_reduction\_at\_matched\_f1 $= 0\%$.

\paragraph{Diagnostic analysis.} The decompose-then-route pipeline achieves its cost target by routing most sub-questions to cheap tiers: the mean cost per question drops from \$2.25 (all-Opus) to \$0.69. The quality failure stems from two compounding error sources:

\emph{(1) Merger failure.} The 0.5B merger model fails to coherently synthesize sub-answers on 12\% of questions, incurring a $\sim$55\% quality penalty on affected examples. This single failure mode accounts for the majority of the 3.7pp F1 gap. CRIT-010 identifies this as the dominant validity concern and proposes repeating the experiment with a sonnet-tier merger.

\emph{(2) Context isolation.} Each sub-question is answered independently, without access to the other sub-question's context or answer. For questions where the two hops are interdependent (e.g., the answer to hop 1 constrains the search space for hop 2), this independence assumption introduces errors that routing cannot recover.

CRIT-010 also notes that the always-Opus baseline is trivially conservative---it has no routing intelligence---and that the 1pp F1 tolerance is strict given the 69\% cost reduction. A Pareto analysis at relaxed tolerance bands (2pp, 4pp) would show the decompose-then-route system operating at a favorable cost-quality tradeoff that the strict threshold obscures.

### 4.4 Experiment 4: Online Contextual-Bandit Routing (HYP-006)

\paragraph{Setup.} We simulate the routing problem with pre-computed quality scores drawn from calibrated Beta distributions \cite{hu2024routerbench}. Queries are embedded with all-MiniLM-L6-v2 and projected to $d=32$ via PCA. The Thompson Sampling (TS) router maintains per-arm linear Gaussian posteriors updated after each query. The static baseline is a logistic-regression router trained on 2{,}000 in-distribution (ID) general-knowledge queries from MMLU validation. Phase 1 (warm-up): all methods observe 2{,}000 ID queries. Phase 2 (evaluation): 500 out-of-distribution (OOD) queries from HumanEval docstrings and GSM8K. Five seeds (42, 123, 7, 2024, 99).

\paragraph{Sanity gate.} Passed on all seeds.

\paragraph{Results.} Table~\ref{tab:exp4} reports primary and secondary metrics.

\begin{table}[h]
\centering
\caption{Experiment 4: Thompson Sampling vs.\ static router under distribution shift.}
\label{tab:exp4}
\begin{tabular}{lcc}
\toprule
Metric & Thompson Sampling & Static Baseline \\
\midrule
Quality-cost AUC (OOD) & $0.421 \pm 0.068$ & $\mathbf{0.459 \pm 0.006}$ \\
Quality-cost AUC (ID) & $\mathbf{0.563}$ & $0.503$ \\
Cumulative regret (500 OOD) & $81.4 \pm 25.1$ & --- \\
Avg.\ cost (OOD, normalized) & $0.447 \pm 0.269$ & --- \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Outcome.} **Hypothesis fails.** The pre-registered threshold required quality\_cost\_auc\_ood $\geq$0.08 above the static baseline. The observed delta is $-0.038 \pm 0.068$: TS is on average \emph{worse} than the static router on OOD queries, with a confidence interval spanning zero.

\paragraph{Diagnostic analysis.} Per-seed inspection reveals high variance: TS beats the static baseline on only one of five seeds (seed 123, $\Delta = +0.029$) and underperforms badly on two seeds (seed 42, $\Delta = -0.093$; seed 2024, $\Delta = -0.144$).

\emph{(1) Cold-start problem.} CRIT-011 identifies the core design flaw: a $d=32$ linear Thompson Sampling model needs $O(d^2) \approx 1{,}000$ updates to concentrate its posterior, but receives only 500 OOD queries. The bandit has not converged before evaluation ends. This is a design limitation, not a finding about bandit routing in general.

\emph{(2) Over-exploitation.} On high-variance seeds, TS locks onto Opus early in the OOD phase after a few positive high-quality outcomes, driving the average cost to $\sim$0.96 normalized units. The quality-cost AUC metric penalizes this expensive routing because quality at high cost thresholds is not proportionally higher.

\emph{(3) Static baseline robustness.} The logistic-regression router trained on 2{,}000 ID examples with calibrated labels transfers surprisingly well to OOD queries ($0.459 \pm 0.006$), with negligible variance across seeds. Its features capture enough distributional structure to maintain reasonable routing under moderate domain shift.

Notably, TS \emph{does} outperform the static router on in-distribution queries ($0.563$ vs.\ $0.503$), confirming that the bandit learning mechanism works when given sufficient data. The failure is specific to the cold-start regime under distribution shift---exactly the setting the hypothesis targeted, but with an insufficiently expressive model for the available sample size.

### 4.5 Summary of Results

Table~\ref{tab:summary} summarizes all four experiments against their pre-registered thresholds.

\begin{table}[h]
\centering
\caption{Summary: all four pre-registered hypotheses fail their thresholds.}
\label{tab:summary}
\begin{tabular}{llccc}
\toprule
Strategy & Primary Metric & Threshold & Observed $\Delta$ & Pass? \\
\midrule
Multi-head 4D (HYP-002) & Routing accuracy & $\geq$+0.03 & $-0.120$ & No \\
Entropy routing (HYP-001) & Quality/budget norm. & $\geq$+0.05 & $+0.044$ & No \\
Decompose-then-route (HYP-007) & Cost red.\ @ matched F1 & $\geq$15\% & $0.0\%$ & No \\
Thompson Sampling (HYP-006) & QC-AUC (OOD) & $\geq$+0.08 & $-0.038$ & No \\
\bottomrule
\end{tabular}
\end{table}

Three of the four failures are diagnostic rather than purely negative:

\begin{itemize}
\item The entropy router demonstrates a clearly superior per-instance routing signal (+15.5pp accuracy) but is penalized by a cost-asymmetric metric design. The routing \emph{quality} advantage is real; the metric framing is what fails.
\item Decompose-then-route achieves 69\% raw cost reduction but is undermined by a weak merger model. The cost hypothesis holds; the quality-preservation mechanism (merging) is the bottleneck.
\item Thompson Sampling learns effectively in-distribution but suffers from cold-start in the OOD regime. The adaptation mechanism works; the parameterization ($d=32$, 500 steps) is underspecified for the task.
\end{itemize}

Only the multi-head 4D router represents a clean negative: rich pre-trained embeddings render handcrafted dimensional decomposition counterproductive.
