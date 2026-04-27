---
{
  "id": "DRAFT-004",
  "type": "DraftSection",
  "created_at": "2026-04-27T05:56:35+00:00",
  "parent_ids": [
    "DRAFT-001",
    "DRAFT-002",
    "DRAFT-003",
    "IDEA-001",
    "HYP-002",
    "HYP-008"
  ],
  "author": "paper-writer",
  "summary": "Related Work v1: input-feature routing, output-conditioned cascades, speculative decoding transplant, multi-tier and batch routing, confidence calibration",
  "body_path": "thoughts/DRAFT-004.md",
  "section": "related-work",
  "version": 1,
  "citation_ids": [
    "CITE-001",
    "CITE-002",
    "CITE-003",
    "CITE-006",
    "CITE-007",
    "CITE-008",
    "CITE-009",
    "CITE-010",
    "CITE-011",
    "CITE-013",
    "CITE-015",
    "CITE-017",
    "CITE-018",
    "CITE-019",
    "CITE-021",
    "CITE-023",
    "CITE-024",
    "CITE-025",
    "CITE-026",
    "CITE-031",
    "CITE-032",
    "CITE-033"
  ],
  "text_path": "thoughts/DRAFT-004.md"
}
---

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
