---
{
  "id": "DRAFT-002",
  "type": "DraftSection",
  "created_at": "2026-04-27T01:32:06+00:00",
  "parent_ids": [
    "DRAFT-001",
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
  "summary": "Abstract v1: four pre-registered routing strategies all fail thresholds; diagnostic negative-results framing",
  "body_path": "thoughts/DRAFT-002.md",
  "section": "abstract",
  "version": 1,
  "citation_ids": [
    "CITE-001",
    "CITE-002",
    "CITE-006",
    "CITE-007",
    "CITE-009",
    "CITE-026",
    "CITE-029",
    "CITE-030"
  ],
  "text_path": "thoughts/DRAFT-002.md"
}
---

## Abstract

Routing queries to the cheapest sufficiently-capable large language model (LLM) is a promising lever for reducing inference cost, yet the design space of routing strategies remains under-explored beyond simple supervised classifiers \cite{ong2024routellm, chen2023frugalgpt}. We pre-register and evaluate four novel routing mechanisms against matched baselines: (1) a multi-dimensional complexity decomposition router that scores queries on four orthogonal difficulty axes \cite{jiang2023llmblender, hu2024routerbench}, (2) an entropy-based router that uses the small model's own token-level uncertainty as an escalation signal \cite{kuhn2023semantic, xiong2023confidence}, (3) a decompose-then-route pipeline that splits multi-hop queries into atomic sub-questions routed independently, and (4) an online contextual-bandit router using Thompson Sampling to adapt under distribution shift \cite{hu2024routerbench}. All four hypotheses fail their pre-registered thresholds. The multi-head router underperforms a single-score logistic baseline by 11.7 percentage points on routing accuracy, demonstrating that rich sentence embeddings already encode the complexity signal that handcrafted decomposition attempts to isolate. The entropy router yields a superior per-instance escalation signal (+15.5pp routing accuracy over text features) but the mandatory small-model inference overhead limits the aggregate quality-at-budget gain to +0.044, narrowly missing the 0.05 threshold. Decompose-then-route achieves 69% raw cost reduction on HotpotQA but degrades answer F1 by 3.7 percentage points---outside the 1pp tolerance---due to a 12% merger failure rate in the sub-answer synthesis step. The Thompson Sampling bandit underperforms the static baseline by 3.8pp on out-of-distribution quality-cost AUC, as 500 adaptation steps are insufficient for a 32-dimensional linear bandit to overcome cold-start. We report these negative results with full pre-registration, per-seed breakdowns, and diagnostic failure analyses, identifying three actionable lessons for future routing research: (i) output-side uncertainty signals are informative but must be amortized to avoid structural cost asymmetry, (ii) sub-query routing requires merger quality guarantees before cost savings materialize, and (iii) online adaptation demands low-dimensional context representations or warm-start initialization to be practical at realistic query volumes.
