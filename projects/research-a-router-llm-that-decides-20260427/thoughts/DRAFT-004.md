---
{
  "id": "DRAFT-004",
  "type": "DraftSection",
  "created_at": "2026-04-27T01:39:04+00:00",
  "parent_ids": [
    "DRAFT-001",
    "DRAFT-003",
    "IDEA-001",
    "HYP-001",
    "HYP-002",
    "HYP-006",
    "HYP-007"
  ],
  "author": "paper-writer",
  "summary": "Related Work v1: LLM routing, uncertainty estimation, query decomposition, online adaptation — positions four hypotheses against prior art",
  "body_path": "thoughts/DRAFT-004.md",
  "section": "related-work",
  "version": 1,
  "citation_ids": [
    "CITE-001",
    "CITE-002",
    "CITE-003",
    "CITE-004",
    "CITE-005",
    "CITE-006",
    "CITE-007",
    "CITE-008",
    "CITE-009",
    "CITE-010",
    "CITE-011",
    "CITE-012",
    "CITE-013",
    "CITE-014",
    "CITE-015",
    "CITE-016",
    "CITE-017",
    "CITE-018",
    "CITE-019",
    "CITE-020",
    "CITE-021",
    "CITE-022",
    "CITE-023",
    "CITE-024",
    "CITE-025",
    "CITE-026",
    "CITE-027",
    "CITE-028",
    "CITE-029",
    "CITE-030",
    "CITE-031"
  ],
  "text_path": "thoughts/DRAFT-004.md"
}
---

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
