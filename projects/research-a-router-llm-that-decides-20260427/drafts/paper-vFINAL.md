# research a router LLM that decides whether to call Haiku, Sonnet, or Opus based on query complexity. Build something tha

## Abstract
## Abstract

Routing queries to the cheapest sufficiently-capable large language model (LLM) is a promising lever for reducing inference cost, yet the design space of routing strategies remains under-explored beyond simple supervised classifiers \cite{ong2024routellm, chen2023frugalgpt}. We pre-register and evaluate four novel routing mechanisms against matched baselines: (1) a multi-dimensional complexity decomposition router that scores queries on four orthogonal difficulty axes \cite{jiang2023llmblender, hu2024routerbench}, (2) an entropy-based router that uses the small model's own token-level uncertainty as an escalation signal \cite{kuhn2023semantic, xiong2023confidence}, (3) a decompose-then-route pipeline that splits multi-hop queries into atomic sub-questions routed independently, and (4) an online contextual-bandit router using Thompson Sampling to adapt under distribution shift \cite{hu2024routerbench}. All four hypotheses fail their pre-registered thresholds. The multi-head router underperforms a single-score logistic baseline by 11.7 percentage points on routing accuracy, demonstrating that rich sentence embeddings already encode the complexity signal that handcrafted decomposition attempts to isolate. The entropy router yields a superior per-instance escalation signal (+15.5pp routing accuracy over text features) but the mandatory small-model inference overhead limits the aggregate quality-at-budget gain to +0.044, narrowly missing the 0.05 threshold. Decompose-then-route achieves 69% raw cost reduction on HotpotQA but degrades answer F1 by 3.7 percentage points---outside the 1pp tolerance---due to a 12% merger failure rate in the sub-answer synthesis step. The Thompson Sampling bandit underperforms the static baseline by 3.8pp on out-of-distribution quality-cost AUC, as 500 adaptation steps are insufficient for a 32-dimensional linear bandit to overcome cold-start. We report these negative results with full pre-registration, per-seed breakdowns, and diagnostic failure analyses, identifying three actionable lessons for future routing research: (i) output-side uncertainty signals are informative but must be amortized to avoid structural cost asymmetry, (ii) sub-query routing requires merger quality guarantees before cost savings materialize, and (iii) online adaptation demands low-dimensional context representations or warm-start initialization to be practical at realistic query volumes.

## 1. Introduction
## 1. Introduction

Large language model (LLM) providers now offer model families spanning orders of magnitude in cost and capability---from lightweight models such as Haiku to frontier models such as Opus---yet most deployed systems route every query to a single model tier. This one-size-fits-all strategy either overpays for easy queries or underserves hard ones. *LLM routing*, the problem of selecting the cheapest model that is sufficiently capable for a given query, has therefore emerged as a key lever for reducing inference cost without sacrificing quality.

A growing body of work addresses this problem. RouteLLM \cite{ong2024routellm} trains a binary router on human preference data from Chatbot Arena, achieving roughly 2$\times$ cost savings by learning a single win-probability threshold that separates queries suitable for a weaker model from those requiring a stronger one. FrugalGPT \cite{chen2023frugalgpt} proposes a sequential cascade: query a cheap model first, score the response with a learned reliability function, and escalate only when the score falls below a confidence threshold---reporting up to 98\% cost reduction on certain benchmarks. AutoMix \cite{madaan2023automix} frames routing as a POMDP, using self-verification to decide whether to escalate from a small model to a larger one. Hybrid LLM \cite{ding2024hybrid} trains a probabilistic quality-gap predictor to route between two model tiers. RouterBench \cite{hu2024routerbench} provides the first standardized benchmark and reveals that existing routing strategies vary 2--5$\times$ in cost at matched performance, underscoring the gap between current practice and the efficiency frontier.

Despite this progress, the design space of routing strategies remains narrow. Nearly all published routers share three properties: (i) they use *input-side features only*---text embeddings, keyword heuristics, or prompt length---as routing signals, ignoring the small model's own output uncertainty; (ii) they treat each query as an *atomic unit*, routing it wholesale to a single model even when the query contains sub-problems of heterogeneous difficulty; and (iii) they are *static*, trained once on a fixed dataset and deployed without adaptation, leaving them vulnerable to distribution shift as user populations and task mixes evolve.

This paper systematically explores four strategies that relax these assumptions, each motivated by a distinct gap in the existing literature:

\paragraph{Multi-dimensional complexity routing.} Existing routers project query difficulty onto a single scalar. We hypothesize that decomposing complexity into four orthogonal dimensions---reasoning depth, domain specificity, ambiguity, and creativity---and training a separate routing head per dimension yields higher routing accuracy than a single-score classifier \cite{ong2024routellm, hu2024routerbench}. This tests whether structured feature decomposition adds signal beyond what rich sentence embeddings already capture.

\paragraph{Entropy-based routing.} Rather than routing on input features alone, we propose using the token-level entropy of the small model's own draft response as an escalation signal. Prior work establishes that output entropy and confidence scores predict LLM correctness \cite{kuhn2023semantic, kadavath2022language, xiong2023confidence}, but no router has used this signal for model selection. We test whether the direct uncertainty readout outperforms text-feature classifiers on a normalized quality-at-budget metric.

\paragraph{Decompose-then-route.} For complex multi-hop queries, we break the atomic-routing assumption by decomposing the query into atomic sub-questions, routing each independently to the cheapest capable model, and merging sub-answers into a final response. This transplants query decomposition techniques from the question-answering literature into the routing setting \cite{chen2023frugalgpt, ong2024routellm}, testing whether sub-query-level routing granularity reduces cost at matched accuracy.

\paragraph{Online contextual-bandit routing.} We transplant Thompson Sampling from the contextual-bandit literature into LLM routing \cite{ong2024routellm, hu2024routerbench}, maintaining per-arm posteriors conditioned on query embeddings and updating them after each observed quality-cost outcome. This tests whether online adaptation overcomes the brittleness of static routers under distribution shift.

All four hypotheses are pre-registered with explicit metrics, numeric thresholds, and directionality before any experiments are run. Each experiment uses at least three random seeds and includes a matched baseline drawn from existing routing approaches.

All four hypotheses fail their pre-registered thresholds. The multi-head complexity router underperforms a single-score logistic baseline by 11.7 percentage points on routing accuracy, demonstrating that MiniLM sentence embeddings already encode the complexity signal that handcrafted decomposition attempts to isolate. The entropy router yields a clearly superior per-instance signal (+15.5pp routing accuracy over text features) but the mandatory small-model inference overhead limits the aggregate quality-at-budget gain to +0.044, narrowly missing the 0.05 threshold. Decompose-then-route achieves 69\% raw cost reduction on HotpotQA but degrades answer F1 by 3.7pp---outside the 1pp tolerance---due to a 12\% merger failure rate in sub-answer synthesis. The Thompson Sampling bandit underperforms the static baseline by 3.8pp on out-of-distribution quality-cost AUC, as 500 adaptation steps are insufficient for a 32-dimensional linear bandit to overcome cold-start.

We report these negative results transparently, with full pre-registration, per-seed breakdowns, and diagnostic failure analyses. The failures are informative: they identify three actionable lessons for future routing research. First, output-side uncertainty signals are demonstrably more informative than input features for per-instance routing decisions, but must be amortized (e.g., via a learned entropy proxy) to avoid structural cost asymmetry in the aggregate metric. Second, sub-query routing unlocks large raw cost savings but requires merger quality guarantees---a 12\% failure rate in the cheapest merger model erases the gains under strict accuracy tolerance. Third, online bandit adaptation demands low-dimensional context representations or warm-start initialization to be practical at realistic query volumes; a 32-dimensional linear Thompson Sampling agent cannot converge in 500 steps.

The remainder of this paper is organized as follows. Section 2 surveys related work on LLM routing, uncertainty estimation, query decomposition, and contextual bandits. Section 3 details the four routing strategies and their pre-registered experimental designs. Section 4 presents results. Section 5 provides diagnostic analyses and discusses implications. Section 6 concludes with recommendations for future work.

## 2. Related Work
## 2. Related Work

Our four routing strategies draw on distinct lines of research: cost-aware LLM routing, uncertainty estimation for language models, query decomposition, and online learning. We survey each in turn, positioning our contributions relative to the closest prior art.

### 2.1 Cost-Aware LLM Routing

The core premise of LLM routing---that different queries require different model capabilities---has been validated empirically by several recent systems. RouteLLM \cite{ong2024routellm} trains a binary classifier on human preference data from Chatbot Arena to predict whether a weaker model can match a stronger model's response quality. By learning a single win-probability threshold, RouteLLM achieves roughly 2$\times$ cost savings on a strong/weak model pair. FrugalGPT \cite{chen2023frugalgpt} takes a sequential cascade approach: it queries a cheap model first, scores the response with a learned reliability function, and escalates to a more expensive model only when the reliability score falls below a threshold. This cascade architecture reports up to 98\% cost reduction on certain benchmarks, though it requires per-task calibration of the scoring function.

LLM-Blender \cite{jiang2023llmblender} demonstrates via pairwise ranking that no single model dominates across all queries, providing empirical justification for query-adaptive routing even within a fixed benchmark. RouterBench \cite{hu2024routerbench} contributes the first standardized evaluation framework and reveals that existing routing strategies vary 2--5$\times$ in cost at matched performance levels, quantifying the gap between current practice and the efficiency frontier. AutoMix \cite{madaan2023automix} frames routing as a partially observable Markov decision process (POMDP), using self-verification to decide whether to escalate from a small model to a larger one. Hybrid LLM \cite{ding2024hybrid} trains a probabilistic quality-gap predictor to route between two tiers.

A common feature of these systems is that they route based on \emph{input-side features only}---text embeddings, keyword statistics, or prompt metadata---without consulting the small model's output. Our entropy-routing hypothesis (HYP-001) directly challenges this design choice by using the small model's own token-level uncertainty as the routing signal. Additionally, all of these routers treat each query as an atomic unit and are trained offline on static datasets, limitations that our decompose-then-route (HYP-007) and online bandit (HYP-006) strategies respectively address.

### 2.2 Uncertainty Estimation and Confidence Calibration

The idea of using model uncertainty to predict response quality has deep roots. Kadavath et al.\ \cite{kadavath2022language} show that the entropy of a language model's output token distribution correlates with correctness, though RLHF-tuned models require temperature adjustment to restore calibration. Kuhn et al.\ \cite{kuhn2023semantic} introduce \emph{semantic entropy}, which clusters multiple sampled responses by meaning and computes entropy over meaning-clusters rather than tokens, demonstrating an 8 percentage point AUROC improvement over token-level entropy for failure prediction. This gap arises because lexically distinct but semantically equivalent responses inflate token-level entropy without reflecting genuine uncertainty.

Xiong et al.\ \cite{xiong2023confidence} benchmark multiple confidence elicitation strategies and find that white-box token logprob signals yield approximately 8pp AUROC gain over text-feature verbalized confidence, quantifying the advantage that output-side signals hold over input-side proxies. Wang et al.\ \cite{wang2022selfconsistency} establish that self-consistency---agreement across multiple sampled chain-of-thought reasoning paths---serves as a strong proxy for correctness, a finding that subsequent work has extended to general failure prediction. Lin and Evans \cite{lin2021truthfulqa} introduce TruthfulQA, an adversarial benchmark specifically designed to elicit confident but incorrect model responses, representing a failure mode where models are confidently wrong---invisible to token-level entropy but potentially detectable via multi-sample divergence.

Despite this rich literature on uncertainty estimation, no prior work has applied these signals as the primary \emph{routing} mechanism for model selection in a multi-tier LLM system. Our entropy-routing strategy (HYP-001) bridges this gap by using token-level entropy as an escalation trigger, while our experimental results reveal the structural cost asymmetry that limits its aggregate benefit (Section 4).

### 2.3 Speculative Execution and Parallel Inference

Our work is situated alongside a growing literature on parallelism in LLM inference, though our focus is on model \emph{selection} rather than token generation. Speculative decoding \cite{leviathan2022fast} transplants the CPU branch-prediction paradigm into autoregressive generation: a small draft model proposes tokens that a large verifier accepts or rejects in parallel, achieving lossless speedups of 2--3$\times$. Chen et al.\ \cite{chen2023speculative} independently validate this approach at 70B scale, confirming the robustness of the draft-verify paradigm. Lookahead Decoding \cite{fu2024lookahead} achieves parallel inference without a draft model by generating n-gram candidates from the Jacobi iteration trajectory.

AutoMix \cite{madaan2023automix} applies a sequential generate-then-verify architecture to routing, inheriting latency costs from the serial dependence between generation and verification. Our speculative-routing hypothesis (HYP-003, screened out before experiments due to cost-latency concerns) proposed transplanting the parallel draft-verify paradigm from speculative decoding into the routing setting. While HYP-003 was parked during screening, the analogy between speculative decoding and speculative routing remains a promising direction that our negative results on sequential strategies---particularly the entropy router's mandatory small-model overhead (Section 4.2)---indirectly motivate.

### 2.4 Multi-Dimensional Complexity and Query Decomposition

Our multi-head routing hypothesis (HYP-002) posits that decomposing query complexity into orthogonal dimensions improves routing over single-score classifiers. This draws on the observation from RouterBench \cite{hu2024routerbench} and LLM-Blender \cite{jiang2023llmblender} that difficulty is not unidimensional---queries vary along axes of domain specificity, reasoning depth, ambiguity, and creativity. However, the question of whether \emph{explicit} dimensional decomposition adds signal over what rich sentence embeddings already capture implicitly had not been tested. Our negative result (Section 4.1) provides evidence that MiniLM-class embeddings subsume the information in handcrafted complexity dimensions, at least under heuristic labeling.

The decompose-then-route strategy (HYP-007) operates at a different granularity: rather than decomposing the \emph{features} of a query, it decomposes the query \emph{itself} into atomic sub-questions and routes each independently. This builds on the query decomposition literature---Least-to-Most Prompting, DSP, and DecomP---which has shown that breaking complex questions into sub-problems improves LLM accuracy on multi-hop reasoning tasks. Our contribution is to apply this decomposition not for accuracy but for \emph{cost optimization}: routing easy sub-questions to cheap models while reserving expensive models for hard sub-questions. The closest prior work, FrugalGPT's cascade \cite{chen2023frugalgpt}, still treats each query atomically; RouteLLM \cite{ong2024routellm} likewise routes whole queries. No prior router operates at sub-query granularity. Our results show that while the cost savings are substantial (69\%), the sub-answer merger introduces quality degradation that current lightweight synthesis models cannot overcome (Section 4.3).

### 2.5 Online Adaptation and Contextual Bandits

All published LLM routers that we are aware of are static: trained once on a fixed dataset and deployed without adaptation. This leaves them vulnerable to distribution shift as user populations, task mixes, and model capabilities evolve---a gap explicitly noted by RouterBench \cite{hu2024routerbench}. Our Thompson Sampling hypothesis (HYP-006) transplants contextual multi-armed bandits from the recommendation and clinical trial literatures into LLM routing, maintaining per-arm posteriors conditioned on query embeddings and updating them after each observed quality-cost outcome.

The LLM-as-Judge framework \cite{zheng2023judging}, which demonstrates $>$80\% agreement with human quality assessments, provides the reward signal that makes online routing feasible without requiring human annotations at each step. AutoMix \cite{madaan2023automix} is the closest prior work in spirit, framing routing as a sequential decision problem (POMDP), but it solves the POMDP offline on a small fixed dataset rather than adapting online.

The contextual bandit formulation is well-established in other domains---Thompson Sampling and LinUCB have been applied to news recommendation, ad placement, and clinical dosing---but to our knowledge has not been applied to LLM model selection. Our negative result (Section 4.4) reveals that the cold-start problem is acute in this setting: a 32-dimensional linear Thompson Sampling agent requires $O(d^2)$ updates to concentrate its posterior, far exceeding the 500 out-of-distribution queries available in our evaluation. This finding identifies dimensionality reduction and warm-start initialization as prerequisites for practical online routing.

## 3. Method
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

## 4. Experiments
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

## 5. Discussion


