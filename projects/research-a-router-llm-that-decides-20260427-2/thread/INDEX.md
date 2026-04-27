# Thread index

_55 artifacts_  

## Idea (1)

| id | author | summary |
|----|--------|---------|
| `IDEA-001` | orchestrator | research a router LLM that decides whether to call Haiku, Sonnet, or Opus based on query complexity. Build something that goes beyond what is already existing and outperforms the baselines that already exist. |

## Hypothesis (6)

| id | author | summary |
|----|--------|---------|
| `HYP-001` | idea-expander | Multi-signal GBDT router trained on query complexity features achieves ≥85% quality retention vs always-large at ≥40% cost reduction |
| `HYP-002` | idea-expander | [Cross-domain: ASR cascade] Confidence-cascade routing where small model self-assesses and escalates improves cost-normalized quality by ≥15% over static single-stage routers |
| `HYP-003` | idea-expander | [Cross-domain: Active Learning] Ensemble-disagreement uncertainty routing reduces hard-query routing error by ≥20% vs deterministic classifier |
| `HYP-004` | idea-expander | RL-tuned routing policy with quality-cost reward achieves ≥10% CNQ improvement over supervised routing at quality floor 0.80 |
| `HYP-005` | idea-expander | [Gap-fill: latency ignored by all prior work] Latency-cost-quality router trained with TTFT-penalized reward achieves >=15% latency-adjusted quality improvement at fixed token-cost budget vs cost-only routers |
| `HYP-006` | idea-expander | [Gap-fill + Cross-domain: recommender bandits] Thompson Sampling bandit router with posterior updates on observed outcomes reduces routing regret >=20% vs static offline router under query-distribution shift |

## LitFinding (21)

| id | author | summary |
|----|--------|---------|
| `LIT-001` | literature-scout | FrugalGPT: supervised LLM cascade achieving 98% cost reduction; key baseline for RL routing comparison |
| `LIT-002` | literature-scout | RouteLLM: binary preference-data router achieving 2x cost reduction; supervised baseline missing 3-tier RL generalization |
| `LIT-003` | literature-scout | AutoMix: POMDP-based routing with self-verification; RL-adjacent but analytically solved, not trained via policy gradient |
| `LIT-004` | literature-scout | Deep Ensembles provide well-calibrated uncertainty via N independently-trained models — direct methodological foundation for committee-disagreement routing in HYP-003 |
| `LIT-005` | literature-scout | FrugalGPT: LLM cascade reduces cost 98% via adaptive query triage; single-signal scoring function leaves multi-feature gap |
| `LIT-006` | literature-scout | Hybrid LLM: quality-aware router with test-time threshold tuning; supervised baseline missing RL end-to-end reward learning |
| `LIT-007` | literature-scout | Bayesian Active Learning with MC Dropout: uncertainty acquisition (BALD) halves labeling cost vs random — cross-domain origin for HYP-003 disagreement routing |
| `LIT-008` | literature-scout | FrugalGPT cascade achieves 98% cost reduction using a single deterministic scorer — key baseline; explicitly cites uncertain-escalation as open problem that HYP-003 addresses |
| `LIT-009` | literature-scout | RouteLLM trains deterministic routers from preference data achieving 2x cost savings — state-of-the-art baseline for HYP-003; no uncertainty estimation or ensemble |
| `LIT-010` | literature-scout | LLM-Blender: ensemble ranking+fusion framework; no cost savings from routing, but MixInstruct quality labels useful for RL reward construction |
| `LIT-011` | literature-scout | RouteLLM: preference-data binary router achieves 2x cost reduction; embedding-only signal is key baseline for HYP-001 multi-signal comparison |
| `LIT-012` | literature-scout | LLM-Blender: no single LLM dominates all tasks; pairwise ranker motivates per-query selection but requires all-model inference |
| `LIT-013` | literature-scout | Hybrid LLM: quality-gap probabilistic router achieves 22-40% cost advantage with <1% quality drop; closest single-signal baseline to HYP-001 |
| `LIT-014` | literature-scout | RouterBench: 405k pre-cached inference outcomes; shows 2-5x cost variation and reveals prior router generalization failures |
| `LIT-015` | literature-scout | AutoMix: POMDP router with self-verification reduces cost 50%+; validates query-difficulty signaling but requires post-generation cascade |
| `LIT-016` | literature-scout | Plex pretrained ensemble extensions improve selective prediction 20-40% vs deterministic baselines — validates uncertainty-guided escalation concept at scale |
| `LIT-017` | literature-scout | Language Models Know What They Know: LLM self-reported P(True) and P(IK) are well-calibrated escalation signals — mechanistic foundation for HYP-002 intrinsic confidence cascade |
| `LIT-018` | literature-scout | On Calibration of Modern Neural Networks: temperature scaling reliably calibrates overconfident deep networks — essential methodology for HYP-002 dev-set threshold calibration |
| `LIT-019` | literature-scout | FrugalGPT cascade validates observe-then-escalate paradigm achieving 98% cost reduction, but uses external learned scorer not intrinsic logprobs — key baseline and gap for HYP-002 |
| `LIT-020` | literature-scout | Two-Pass End-to-End ASR: streaming RNN-T + LAS second pass yields 17-22% WER reduction via beam-score-triggered cascade — exact cross-domain blueprint for HYP-002 confidence cascade |
| `LIT-021` | literature-scout | AutoMix POMDP cascade uses separate NLI verifier achieving 50%+ cost savings — closest prior art to HYP-002 but requires external verifier model unlike intrinsic logprob approach |

## Citation (20)

| id | author | summary |
|----|--------|---------|
| `CITE-001` | novelty-checker | HYP-004 vs 2305.05176: score 0.3015 |
| `CITE-002` | novelty-checker | HYP-004 vs 2406.18665: score 0.2626 |
| `CITE-003` | novelty-checker | HYP-004 vs 2310.12963: score 0.2504 |
| `CITE-004` | novelty-checker | HYP-003 vs 1612.01474: score 0.3154 |
| `CITE-005` | novelty-checker | HYP-001 vs 2305.05176: score 0.3087 |
| `CITE-006` | novelty-checker | HYP-004 vs 2404.14618: score 0.2977 |
| `CITE-007` | novelty-checker | HYP-003 vs 2305.05176: score 0.3272 |
| `CITE-008` | novelty-checker | HYP-003 vs 2406.18665: score 0.2696 |
| `CITE-009` | novelty-checker | HYP-004 vs 2306.02561: score 0.3034 |
| `CITE-010` | novelty-checker | HYP-001 vs 2406.18665: score 0.2611 |
| `CITE-011` | novelty-checker | HYP-001 vs 2306.02561: score 0.294 |
| `CITE-012` | novelty-checker | HYP-001 vs 2404.14618: score 0.3001 |
| `CITE-013` | novelty-checker | HYP-001 vs 2403.12031: score 0.248 |
| `CITE-014` | novelty-checker | HYP-001 vs 2310.12963: score 0.2496 |
| `CITE-015` | novelty-checker | HYP-003 vs 2207.07411: score 0.2717 |
| `CITE-016` | novelty-checker | HYP-002 vs 2207.05221: score 0.2316 |
| `CITE-017` | novelty-checker | HYP-002 vs 1706.04599: score 0.2654 |
| `CITE-018` | novelty-checker | HYP-002 vs 2305.05176: score 0.3166 |
| `CITE-019` | novelty-checker | HYP-002 vs 1908.10992: score 0.2513 |
| `CITE-020` | novelty-checker | HYP-002 vs 2310.12963: score 0.2541 |

## Critique (6)

| id | author | summary |
|----|--------|---------|
| `CRIT-001` | critic | Boredom critique: synthetic latency + metric circularity undermine novelty |
| `CRIT-002` | critic | HYP-004 frames RL routing as straightforward REINFORCE application; lacks conceptual novelty vs RL baselines |
| `CRIT-003` | critic | Multi-signal GBDT routing is incremental, uses standard tools, saturated problem space |
| `CRIT-004` | critic | HYP-002 cascade router: intrinsic confidence triggers are incremental vs FrugalGPT/AutoMix/ASR precedent |
| `CRIT-005` | critic | [Boredom] Ensemble disagreement is an old, well-validated technique; modest novelty over Plex baseline |
| `CRIT-006` | critic | Boredom: straightforward bandit transplant with circular evaluation metric |

## ExperimentPlan (1)

| id | author | summary |
|----|--------|---------|
| `EXP-001` | experiment-designer | REINFORCE routing policy vs supervised GBDT baseline on RouterBench; 3 seeds, λ-sweep, CNQ at quality floor 0.80 |
