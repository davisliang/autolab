---
{
  "id": "DRAFT-003",
  "type": "DraftSection",
  "created_at": "2026-04-27T01:35:25+00:00",
  "parent_ids": [
    "DRAFT-001",
    "DRAFT-002",
    "IDEA-001",
    "HYP-001",
    "HYP-002",
    "HYP-006",
    "HYP-007",
    "RES-001",
    "RES-002",
    "RES-003",
    "RES-004",
    "CRIT-008",
    "CRIT-009",
    "CRIT-010",
    "CRIT-011"
  ],
  "author": "paper-writer",
  "summary": "Introduction v1: motivates LLM routing, surveys prior work, introduces four pre-registered strategies, previews negative results and diagnostic lessons",
  "body_path": "thoughts/DRAFT-003.md",
  "section": "introduction",
  "version": 1,
  "citation_ids": [
    "CITE-001",
    "CITE-002",
    "CITE-006",
    "CITE-007",
    "CITE-008",
    "CITE-009",
    "CITE-016",
    "CITE-017",
    "CITE-018",
    "CITE-019",
    "CITE-020",
    "CITE-026",
    "CITE-027",
    "CITE-029",
    "CITE-030",
    "CITE-031"
  ],
  "text_path": "thoughts/DRAFT-003.md"
}
---

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
