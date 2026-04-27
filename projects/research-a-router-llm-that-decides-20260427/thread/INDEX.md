# Thread index

_90 artifacts_  

## Idea (1)

| id | author | summary |
|----|--------|---------|
| `IDEA-001` | orchestrator | research a router LLM that decides whether to call Haiku, Sonnet, or Opus based on query complexity. Build something that goes beyond what is already existing and outperforms the baselines that already exist. |

## Hypothesis (7)

| id | author | summary |
|----|--------|---------|
| `HYP-001` | idea-expander | Small-model output entropy as routing signal outperforms text-feature classifiers on quality-cost tradeoff |
| `HYP-002` | idea-expander | Multi-dimensional query complexity decomposition improves routing accuracy over single-score routers |
| `HYP-003` | idea-expander | Speculative routing (CPU branch-prediction transplant) reduces end-to-end latency ≥15% vs sequential routing at matched quality |
| `HYP-004` | idea-expander | RL-trained router with LLM-judge reward achieves Pareto-dominant quality-cost curve vs supervised routers |
| `HYP-005` | idea-expander | Consistency-based routing via repeated Haiku sampling divergence outperforms single-sample entropy routing |
| `HYP-006` | idea-expander | Online contextual-bandit router updated via Thompson Sampling outperforms static supervised router by ≥8pp quality-cost AUC under distribution shift |
| `HYP-007` | idea-expander | Decompose-then-route reduces cost ≥15% vs whole-query routing at matched accuracy on multi-hop QA by routing sub-questions independently |

## LitFinding (25)

| id | author | summary |
|----|--------|---------|
| `LIT-001` | literature-scout | RouteLLM: single win-probability scalar routing trained on human preference data achieves 2x cost savings |
| `LIT-002` | literature-scout | FrugalGPT: LLM cascade with single reliability scoring function cuts inference cost 98% at matched accuracy |
| `LIT-003` | literature-scout | FrugalGPT: sequential LLM cascade framework — establishes route-then-call as the sequential baseline HYP-003 aims to beat |
| `LIT-004` | literature-scout | LLM-Blender: pairwise ranking over candidate outputs reveals that different queries optimally match different LLMs |
| `LIT-005` | literature-scout | RouterBench: first standardized benchmark revealing routing strategies vary 2-5x in cost at matched performance across tasks |
| `LIT-006` | literature-scout | RouteLLM: preference-data trained binary router achieving 2x+ cost savings — sequential pre-call routing baseline for HYP-003 |
| `LIT-007` | literature-scout | RouteLLM supervised preference-based routing: 2x cost reduction baseline with no RL component |
| `LIT-008` | literature-scout | FrugalGPT cascade with scoring function: 98% cost reduction but sequential multi-call, not RL |
| `LIT-009` | literature-scout | LLM-as-Judge validated at >80% human agreement; key reward-signal foundation for HYP-004 RL loop |
| `LIT-010` | literature-scout | Speculative Decoding (Leviathan et al.): CPU speculative execution transplanted to token generation — direct conceptual ancestor of HYP-003 |
| `LIT-011` | literature-scout | AutoMix POMDP router validates sequential decision framework beats supervised routing; closest prior to RL routing |
| `LIT-012` | literature-scout | Speculative Sampling (Chen et al., DeepMind): concurrent validation of speculative draft-verify at 70B scale — confirms robustness of CPU-transplant principle |
| `LIT-013` | literature-scout | Hybrid LLM probabilistic router: supervised quality-gap routing, strong binary baseline with no RL |
| `LIT-014` | literature-scout | AutoMix: POMDP-based self-verify-then-route cascade — sequential architecture shows why generate-then-verify adds latency, motivating HYP-003 |
| `LIT-015` | literature-scout | Lookahead Decoding: draft-free parallel n-gram generation for LLM inference — shows async parallelism gains without draft model, complementary mechanism to HYP-003 |
| `LIT-016` | literature-scout | Self-consistency via diverse sampling provides inter-sample agreement as correctness proxy — foundation for divergence-based routing |
| `LIT-017` | literature-scout | Semantic entropy: cluster K sampled responses by meaning, entropy over meaning-clusters beats token-level entropy at predicting LLM accuracy |
| `LIT-018` | literature-scout | Showing LLMs many of their own samples before self-evaluation improves P(True) — multi-sample context boosts uncertainty estimation |
| `LIT-019` | literature-scout | Consistency across K responses is the best black-box failure-prediction signal; white-box gap is narrow (0.522 vs 0.605 AUROC) |
| `LIT-020` | literature-scout | TruthfulQA: adversarial benchmark where models are confidently wrong — ideal stress-test for divergence routing over entropy routing |
| `LIT-021` | literature-scout | RouteLLM: input-text-feature-only router baseline with 2x cost savings — no output-side entropy signal used |
| `LIT-022` | literature-scout | FrugalGPT cascade: 98% cost reduction via output reliability scorer — supervised cascade baseline with per-task calibration overhead |
| `LIT-023` | literature-scout | Semantic Uncertainty: token-level entropy is noisy due to lexical equivalence — 8pp AUROC gap vs semantic entropy for failure prediction |
| `LIT-024` | literature-scout | LMs (Mostly) Know What They Know: entropy of output token distribution predicts correctness; RLHF miscalibration requires temperature tuning |
| `LIT-025` | literature-scout | Confidence elicitation benchmark: token logprob (white-box) yields ~8pp AUROC gain over text-feature verbalized confidence — quantifies HYP-001's expected advantage |

## Citation (31)

| id | author | summary |
|----|--------|---------|
| `CITE-001` | novelty-checker | Novelty check: HYP-001 vs LIT-021 arxiv:2406.18665 |
| `CITE-002` | novelty-checker | Novelty check: HYP-001 vs LIT-022 arxiv:2305.05176 |
| `CITE-003` | novelty-checker | Novelty check: HYP-001 vs LIT-023 arxiv:2302.09664 |
| `CITE-004` | novelty-checker | Novelty check: HYP-001 vs LIT-024 arxiv:2207.05221 |
| `CITE-005` | novelty-checker | Novelty check: HYP-001 vs LIT-025 arxiv:2306.13063 |
| `CITE-006` | novelty-checker | Novelty check: HYP-002 vs LIT-001 arxiv:2406.18665 |
| `CITE-007` | novelty-checker | Novelty check: HYP-002 vs LIT-002 arxiv:2305.05176 |
| `CITE-008` | novelty-checker | Novelty check: HYP-002 vs LIT-004 arxiv:2306.02561 |
| `CITE-009` | novelty-checker | Novelty check: HYP-002 vs LIT-005 arxiv:2403.12031 |
| `CITE-010` | novelty-checker | Novelty check: HYP-003 vs LIT-003 arxiv:2305.05176 |
| `CITE-011` | novelty-checker | Novelty check: HYP-003 vs LIT-006 arxiv:2406.18665 |
| `CITE-012` | novelty-checker | Novelty check: HYP-003 vs LIT-010 arxiv:2211.17192 |
| `CITE-013` | novelty-checker | Novelty check: HYP-003 vs LIT-012 arxiv:2302.01318 |
| `CITE-014` | novelty-checker | Novelty check: HYP-003 vs LIT-014 arxiv:2310.12963 |
| `CITE-015` | novelty-checker | Novelty check: HYP-003 vs LIT-015 arxiv:2402.02057 |
| `CITE-016` | novelty-checker | Novelty check: HYP-004 vs LIT-007 arxiv:2406.18665 |
| `CITE-017` | novelty-checker | Novelty check: HYP-004 vs LIT-008 arxiv:2305.05176 |
| `CITE-018` | novelty-checker | Novelty check: HYP-004 vs LIT-009 arxiv:2306.05685 |
| `CITE-019` | novelty-checker | Novelty check: HYP-004 vs LIT-011 arxiv:2310.12963 |
| `CITE-020` | novelty-checker | Novelty check: HYP-004 vs LIT-013 arxiv:2404.14618 |
| `CITE-021` | novelty-checker | Novelty check: HYP-005 vs LIT-016 arxiv:2203.11171 |
| `CITE-022` | novelty-checker | Novelty check: HYP-005 vs LIT-017 arxiv:2302.09664 |
| `CITE-023` | novelty-checker | Novelty check: HYP-005 vs LIT-018 arxiv:2207.05221 |
| `CITE-024` | novelty-checker | Novelty check: HYP-005 vs LIT-019 arxiv:2306.13063 |
| `CITE-025` | novelty-checker | Novelty check: HYP-005 vs LIT-020 arxiv:2109.07958 |
| `CITE-026` | novelty-checker | Novelty check: HYP-006 vs LIT-001 arxiv:2406.18665 |
| `CITE-027` | novelty-checker | Novelty check: HYP-006 vs LIT-005 arxiv:2403.12031 |
| `CITE-028` | novelty-checker | Novelty check: HYP-006 vs LIT-007 arxiv:2406.18665 |
| `CITE-029` | novelty-checker | Novelty check: HYP-007 vs LIT-001 arxiv:2406.18665 |
| `CITE-030` | novelty-checker | Novelty check: HYP-007 vs LIT-002 arxiv:2305.05176 |
| `CITE-031` | novelty-checker | Novelty check: HYP-007 vs LIT-005 arxiv:2403.12031 |

## Critique (11)

| id | author | summary |
|----|--------|---------|
| `CRIT-001` | screen-boredom | Speculative routing cost-latency tradeoff breaks CPU analogy; misprediction penalty makes 15% latency target unrealistic |
| `CRIT-002` | critic | Medium-severity boredom: output entropy routing concept is straightforward application of well-established failure-prediction techniques; empirical comparison fills gap but risk of replication result |
| `CRIT-003` | critic | HYP-002: incremental multi-head routing lacks novelty; handcrafted decomposition without causal mechanism |
| `CRIT-004` | critic | HYP-004 applies established POMDP RL to routing; AutoMix prior art + modest novelty threshold → HIGH boredom risk |
| `CRIT-005` | critic | Boredom critique—consistency routing is incremental over known uncertainty signals; 3x Haiku cost for 4pp gain unclear |
| `CRIT-006` | screen-boredom | Thompson Sampling is predictable application of bandit literature; context encoding remains unspecified. |
| `CRIT-007` | critic | HYP-007: decompose-then-route is straightforward composition with scoped empirical value and overhead risks |
| `CRIT-008` | critic | Validity critique of RES-001: noisy heuristic labels, tiny dataset, no significance test; null result directionally informative but mechanistically confounded |
| `CRIT-009` | critic | Validity critique of RES-002: cost-asymmetric metric design, narrow miss not significant at 3 seeds, proxy model may not generalize |
| `CRIT-010` | critic | Validity critique of RES-003: weak merger is dominant failure mode, always-Opus baseline trivially conservative, strict F1 tolerance hides Pareto value |
| `CRIT-011` | critic | Validity critique of RES-004: d=384 LinTS needs 150k updates but gets 500 — cold-start is design flaw not finding; result not significant |

## ExperimentPlan (4)

| id | author | summary |
|----|--------|---------|
| `EXP-001` | experiment-designer | Multi-head 4D routing vs single-score baseline on MMLU+GSM8K+AlpacaEval proxy labels |
| `EXP-002` | experiment-designer | Entropy-router vs text-feature router on MMLU subset using MLX small/large model pair |
| `EXP-003` | experiment-designer | Decompose-then-route vs whole-query routing on HotpotQA subset with simulated 3-tier cost model |
| `EXP-004` | experiment-designer | Contextual Thompson Sampling router vs static supervised baseline under simulated distribution shift on MMLU+HumanEval proxy |

## ExperimentResult (4)

| id | author | summary |
|----|--------|---------|
| `RES-001` | experiment-runner | EXP-001 result: multi-head 4D router FAILS to outperform single-score baseline — baseline wins routing_accuracy by +11.7pp |
| `RES-002` | experiment-runner | EXP-002 result: entropy router FAILS pre-registered threshold — wins quality_at_budget_normalized by +0.044 (threshold was ≥0.05), limited by mandatory small-model cost overhead |
| `RES-003` | experiment-runner | EXP-003 result: decompose-then-route FAILS pre-registered threshold — raw cost reduction 69% but F1 degrades 3.7pp (outside 1pp tolerance), so cost_reduction_at_matched_f1=0 |
| `RES-004` | experiment-runner | EXP-004 result: Thompson Sampling router FAILS pre-registered threshold — mean delta=-0.038 ± 0.068 (threshold ≥+0.08), TS underperforms static on OOD AUC |

## DraftSection (7)

| id | author | summary |
|----|--------|---------|
| `DRAFT-001` | paper-writer | Paper outline v1: four pre-registered routing strategies, all negative results, diagnostic insights |
| `DRAFT-002` | paper-writer | Abstract v1: four pre-registered routing strategies all fail thresholds; diagnostic negative-results framing |
| `DRAFT-003` | paper-writer | Introduction v1: motivates LLM routing, surveys prior work, introduces four pre-registered strategies, previews negative results and diagnostic lessons |
| `DRAFT-004` | paper-writer | Related Work v1: LLM routing, uncertainty estimation, query decomposition, online adaptation — positions four hypotheses against prior art |
| `DRAFT-005` | paper-writer | Method v1: problem formulation, four pre-registered routing strategies, experimental protocols, baselines and metrics |
| `DRAFT-006` | paper-writer | Experiments v1: four pre-registered strategies all fail thresholds; diagnostic analysis of failure modes |
| `DRAFT-007` | paper-writer | Discussion v1: diagnostic lessons from four negative results, threats to validity, and recommendations for future routing research |
