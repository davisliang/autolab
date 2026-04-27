# Thread index

_140 artifacts_  

## Idea (1)

| id | author | summary |
|----|--------|---------|
| `IDEA-001` | orchestrator | research a router LLM that decides whether to call Haiku, Sonnet, or Opus based on query complexity. Build something that goes beyond what is already existing and outperforms the baselines that already exist. One obvious baseline is to always use Haiku/Sonnet/Opus. Another baseline that's obvious is to use a Haiku model to first determine which downstream model the query should be routed to. |

## Hypothesis (8)

| id | author | summary |
|----|--------|---------|
| `HYP-001` | idea-expander | A lightweight distilbert-based classifier routes Haiku/Sonnet/Opus more cost-efficiently than a Haiku LLM router |
| `HYP-002` | idea-expander | Speculative cascade execution (cross-domain transplant from speculative decoding) outperforms input-feature routing on GSM8K cost savings |
| `HYP-003` | idea-expander | Multi-signal routing (embedding + syntax features via logistic regression) achieves ≥85% agreement with oracle routing labels on MMLU |
| `HYP-004` | idea-expander | Confidence-cascade routing with Platt-scaled dynamic thresholds reduces API cost ≥20% vs. fixed-threshold routing at matched quality |
| `HYP-005` | idea-expander | 3-tier Haiku/Sonnet/Opus routing Pareto-dominates binary Haiku/Opus routing: middle tier earns its complexity by ≥3pp quality gain at ≥1 matched-cost operating point on MMLU |
| `HYP-006` | idea-expander | Online contextual-bandit routing updates thresholds from deployment outcomes, achieving ≥15% additional cost reduction over static router after 500 queries on a distribution-shifted stream |
| `HYP-007` | idea-expander | Conversation-history routing: rolling prior-turn difficulty features reduce strong-model calls ≥15% vs. per-query router at matched quality on simulated multi-turn MMLU |
| `HYP-008` | idea-expander | Portfolio batch routing: knapsack-style budget allocation over a batch reduces API cost ≥20% vs. independent per-query routing at matched aggregate quality on RouterBench |

## LitFinding (64)

| id | author | summary |
|----|--------|---------|
| `LIT-001` | literature-scout | FrugalGPT: cascade routing reduces LLM API cost up to 98% by learning per-query model combinations |
| `LIT-002` | literature-scout | Calibration of Modern Neural Networks: temperature scaling (Platt variant) is the most effective post-hoc confidence calibration method |
| `LIT-003` | literature-scout | RouteLLM: training routers from preference data achieves 2x cost savings while maintaining LLM response quality |
| `LIT-004` | literature-scout | Language Models Know What They Know: larger LLMs produce usable P(True) self-assessment signals calibrated across diverse tasks |
| `LIT-005` | literature-scout | Semantic Uncertainty: entropy over semantically equivalent outputs better predicts LLM accuracy than token-level confidence |
| `LIT-006` | literature-scout | FrugalGPT: LLM cascade with learned scoring achieves 98% cost reduction matching GPT-4; cascade-on-response baseline vs HYP-001 pre-routing |
| `LIT-007` | literature-scout | DINCO: verbalized LLM confidence is overconfident due to suggestibility; distractor normalization significantly improves calibration (ICLR 2026) |
| `LIT-008` | literature-scout | RouteLLM: BERT-style router on human preference data achieves 2x+ cost savings on MMLU; most direct prior-art comparison to HYP-001 |
| `LIT-009` | literature-scout | Hybrid LLM: BERT-based binary router reduces large model calls 40% with <1% quality drop; pre-routing without model output access |
| `LIT-010` | literature-scout | AutoMix: POMDP router with few-shot self-verification achieves 50%+ cost reduction; requires model inference for routing signal unlike HYP-001 |
| `LIT-011` | literature-scout | Sentence-embedding + kNN correctness predictors route across MMLU/HELM, directly matching HYP-003 approach |
| `LIT-012` | literature-scout | EcoAssistant: hierarchical LLM cascade with solution caching surpasses GPT-4 by 10pp at <50% cost; corroborates weak-to-strong escalation value |
| `LIT-013` | literature-scout | FrugalGPT LLM cascade with DistilBERT scoring achieves 98% cost reduction vs GPT-4 at matched accuracy |
| `LIT-014` | literature-scout | DeBERTa router predicts quality gap between small/large LLM; 40% fewer large-model calls at no quality drop |
| `LIT-015` | literature-scout | RouterBench: 405k outcomes across 11 models/8 datasets; predictive embedding classifiers reduce cost 2-5x at matched quality |
| `LIT-016` | literature-scout | RouteLLM: preference-data routers (kNN embedding, DeBERTa, MF) reduce strong-model calls 2x+ with no quality drop on MMLU |
| `LIT-017` | literature-scout | Source-domain for HYP-002 cross-domain transplant: token-level speculative accept/reject (Leviathan et al. 2023) lifted to model-level cascade |
| `LIT-018` | literature-scout | Independent speculative decoding (Chen et al. / DeepMind 2023): 2-2.5x speedup; acceptance rate key; heterogeneous difficulty benefits most |
| `LIT-019` | literature-scout | FrugalGPT input-feature cascade baseline: 98% cost reduction vs GPT-4; routes before generation — cannot observe output quality, HYP-002 target to beat |
| `LIT-020` | literature-scout | RouteLLM: strongest 2024 input-feature router via preference data, 2x cost reduction on GSM8K — primary numeric baseline for HYP-002 |
| `LIT-021` | literature-scout | Let's Verify Step by Step: PRMs outperform outcome-only judges for math; informs HYP-002 judge design risk and mitigation path |
| `LIT-022` | literature-scout | LLM-Blender PairRanker: output-conditioned selection outperforms input-feature routing, validating HYP-002 premise; but runs all models — HYP-002 avoids this |
| `LIT-023` | literature-scout | CALM: early exit at intermediate Transformer layers achieves 3x speedup with statistical quality guarantees — avoids speculative cascade structural overhead |
| `LIT-024` | literature-scout | Learning to Defer: jointly trained classifier+rejector achieves Bayes-optimal deferral cost boundary — replaces HYP-002 hand-crafted judge with theoretically grounded learned decision rule |
| `LIT-025` | literature-scout | Adaptive Computation Time (Graves 2016): differentiable per-input compute allocation — theoretical foundation for end-to-end trainable routing with explicit cost penalties |
| `LIT-026` | literature-scout | Self-Consistency: majority vote over multiple chain-of-thought samples is a calibrated confidence proxy — more reliable than single verbalized confidence for routing |
| `LIT-027` | literature-scout | ComplexityNet: fine-tuned small LM achieves 79% task complexity accuracy, 90% compute reduction vs always-large baseline |
| `LIT-028` | literature-scout | Conformal Language Modeling: distribution-free coverage guarantees for LM outputs via calibrated stopping rules — principled alternative to Platt-scaled routing thresholds |
| `LIT-029` | literature-scout | Unified routing+cascading: optimal strategy is linear cost-quality tradeoff; quality estimator fidelity is the sole critical factor |
| `LIT-030` | literature-scout | Batch Calibration: LLM verbalized confidence is systematically biased by prompt format and ICL examples; zero-cost BC debiasing precedes reliable Platt calibration |
| `LIT-031` | literature-scout | DSC benchmark: BERT-based routers use category heuristics not complexity signals; all coding/math routed to strongest model regardless of difficulty |
| `LIT-032` | literature-scout | SLM front-door routing benchmark: LLM router fails latency gate; SLMs achieve zero-marginal-cost routing; 6-8pp accuracy gap is remaining barrier |
| `LIT-033` | literature-scout | Cross-Model Perplexity: training-free label-free routing signal; AUROC 0.75 on MMLU vs 0.59 for within-model entropy; catches confident errors classifiers miss |
| `LIT-034` | literature-scout | TRACER: LLM production traces as free training labels; lightweight surrogate fully replaces Sonnet 4.6 on 150-class intent; 83-100% cost reduction |
| `LIT-035` | literature-scout | SLM learns to proactively seek LLM help: dynamic collaboration outperforms static routing; stronger SLMs self-escalate less; strategies transfer to unseen LLMs |
| `LIT-036` | literature-scout | Training-free online routing via ANN: 1.85x cost efficiency; offline classifiers criticized for latency overhead and costly retraining — confirms HYP-001 production limitations |
| `LIT-037` | literature-scout | Survey of multi-LLM routing: most methods are binary; multi-tier routing is open challenge; cluster-based routing Pareto-dominates single models |
| `LIT-038` | literature-scout | FORC routes among 4 LLMs via meta-model, matches largest LLM at 63% cost reduction; multi-tier pool is key to efficiency |
| `LIT-039` | literature-scout | Triage analytically derives conditions for middle LLM tier cost-effectiveness in 3-tier (Haiku/Sonnet/Opus-parallel) routing for SWE-bench |
| `LIT-040` | literature-scout | MetaLLM multi-armed bandit routes among multiple LLMs; defaulting to best single model is suboptimal; 3+ tier pool improves accuracy-cost efficiency |
| `LIT-041` | literature-scout | Eagle training-free ELO router for multi-LLM inference: 23.52% AUC improvement; local ELO implicitly discovers model-specific query zones |
| `LIT-042` | literature-scout | Semantic agreement (meaning-level consensus over ensemble outputs) is a training-free black-box routing signal: 40% cost, 60% latency reduction vs target-model-only |
| `LIT-043` | literature-scout | Reward-Guided Speculative Decoding (RSD): PRM evaluates intermediate reasoning steps to adaptively invoke target model, achieving 4.4x fewer FLOPs at +3.5pp accuracy over standard speculative decoding |
| `LIT-044` | literature-scout | Cascadia: bi-level MILP+Chebyshev co-optimization of cascade deployment and routing achieves 4x tighter latency SLOs and 5x higher throughput vs single-model; system co-optimization is necessary for efficient cascade serving |
| `LIT-045` | literature-scout | Trained verifiers on GSM8K provide same performance boost as 30x model size increase, scale better than finetuning; foundational evidence that learned judges dramatically outperform heuristics for math cascade routing |
| `LIT-046` | literature-scout | Routing collapse: routers systematically default to most expensive model due to objective-decision mismatch between scalar quality prediction and discrete model comparison; EquiRouter (ranking-based) mitigates collapse for 17% cost reduction |
| `LIT-047` | literature-scout | CoSine collaborative speculative inference: expertise-based request routing to specialized drafters with confidence-based token fusion achieves 23.2% lower latency and 32.5% higher throughput vs SOTA; pipelining draft/verify eliminates serial overhead |
| `LIT-048` | literature-scout | ZOOTER proves complementary potential of multi-LLM pool: oracle routing over 6 same-size models outperforms BMA on all subtasks; heterogeneous expertise zones exist even within same model size tier |
| `LIT-049` | literature-scout | STEER validates binary 2-tier routing as strong baseline: stepwise confidence routing achieves +20% accuracy and 48% fewer FLOPs vs always-large on AIME; 3-tier extension not tested — gap HYP-005 fills |
| `LIT-050` | literature-scout | Embedding+kNN correctness predictors on 29 HELM tasks; single-signal baseline HYP-003 directly extends with syntax features |
| `LIT-051` | literature-scout | ZOOTER: reward-guided routing distills 86M mDeBERTa classifier from RM silver labels, outperforms best single model on 44% of 26-subset benchmark — validates small-classifier routing with silver supervision |
| `LIT-052` | literature-scout | DSC benchmark: Anthropic Haiku/Sonnet 2-tier router routes 7% LeetCode-Easy to Sonnet but 80% MT-Bench Math; category heuristics dominate complexity signals even in commercial binary routers |
| `LIT-053` | literature-scout | ComplexityNet: fine-tuned small LM achieves 79% complexity accuracy and 90% compute reduction; links routing accuracy to cost efficiency on MBPP |
| `LIT-054` | literature-scout | RouterBench convex-hull theorem: 3-tier Pareto-dominates 2-tier iff Sonnet point lies above Haiku-Opus line; MMLU data across 11 models available for oracle oracle 2-tier vs 3-tier comparison |
| `LIT-055` | literature-scout | ZOOTER distills reward scores into lightweight routing function with tag-based enhancement; validates task-type categorical signal for routing |
| `LIT-056` | literature-scout | RouterBench 405k outcomes with CQ-score metric: 1pp routing accuracy ≈ 2-3% cost savings on MMLU; bridges routing accuracy to cost efficiency |
| `LIT-057` | literature-scout | Hybrid LLM: DeBERTa router predicts quality gap from input alone; soft labels > hard oracle labels — informs HYP-003 label strategy and sets upper-bound on LR savings |
| `LIT-058` | literature-scout | Blending Is All You Need: random stochastic selection among 3 small models (6-13B) beats ChatGPT 175B in 30-day A/B tests — validates complementary model expertise without any input-based routing |
| `LIT-059` | literature-scout | DistilBERT: 66M-param knowledge-distilled BERT variant is 60% faster and 40% smaller than BERT-base, retaining 97% GLUE performance — quantifies near-zero routing overhead vs Haiku API call |
| `LIT-060` | literature-scout | Adaptive conformal inference provably maintains coverage under unknown distribution shift via a single online-updated parameter — theoretical backbone for HYP-004 rolling threshold |
| `LIT-061` | literature-scout | R-Tuning reveals LLMs produce structurally overconfident verbalized scores on unknowns because standard fine-tuning forces completion — Platt scaling cannot fix fundamental miscalibration above coverage ceiling |
| `LIT-062` | literature-scout | Selective classification framework: user-specified risk level maps to confidence threshold for reject-or-predict — foundational theory for HYP-004 cascade threshold design and coverage-risk tradeoff |
| `LIT-063` | literature-scout | Consistent surrogate loss for learning-to-defer: joint classifier+rejector training achieves Bayes-optimal deferral boundary — HYP-004 fixed-threshold cascade is suboptimal vs. learned rejector |
| `LIT-064` | literature-scout | Weighted conformal prediction maintains distribution-free calibration under covariate shift via likelihood ratio reweighting — provides theoretical bound on HYP-004 threshold drift across MMLU/GSM8K |

## Citation (33)

| id | author | summary |
|----|--------|---------|
| `CITE-001` | novelty-checker | Verified novelty: HYP-001 vs arxiv 2305.05176 (score=0.2997) |
| `CITE-002` | novelty-checker | Verified novelty: HYP-001 vs arxiv 2406.18665 (score=0.2555) |
| `CITE-003` | novelty-checker | Verified novelty: HYP-001 vs arxiv 2404.14618 (score=0.2812) |
| `CITE-004` | novelty-checker | Verified novelty: HYP-001 vs arxiv 2310.12963 (score=0.2494) |
| `CITE-005` | novelty-checker | Verified novelty: HYP-001 vs arxiv 2310.03046 (score=0.2619) |
| `CITE-006` | novelty-checker | Verified novelty: HYP-002 vs arxiv 2211.17192 (score=0.2797) |
| `CITE-007` | novelty-checker | Verified novelty: HYP-002 vs arxiv 2302.01318 (score=0.3310) |
| `CITE-008` | novelty-checker | Verified novelty: HYP-002 vs arxiv 2305.05176 (score=0.3108) |
| `CITE-009` | novelty-checker | Verified novelty: HYP-002 vs arxiv 2406.18665 (score=0.2689) |
| `CITE-010` | novelty-checker | Verified novelty: HYP-002 vs arxiv 2305.20050 (score=0.1868) |
| `CITE-011` | novelty-checker | Verified novelty: HYP-002 vs arxiv 2306.02561 (score=0.3077) |
| `CITE-012` | novelty-checker | Verified novelty: HYP-003 vs arxiv 2309.15789 (score=0.2978) |
| `CITE-013` | novelty-checker | Verified novelty: HYP-003 vs arxiv 2305.05176 (score=0.3078) |
| `CITE-014` | novelty-checker | Verified novelty: HYP-003 vs arxiv 2404.14618 (score=0.2954) |
| `CITE-015` | novelty-checker | Verified novelty: HYP-003 vs arxiv 2403.12031 (score=0.2536) |
| `CITE-016` | novelty-checker | Verified novelty: HYP-003 vs arxiv 2406.18665 (score=0.2713) |
| `CITE-017` | novelty-checker | Verified novelty: HYP-004 vs arxiv 2305.05176 (score=0.3003) |
| `CITE-018` | novelty-checker | Verified novelty: HYP-004 vs arxiv 1706.04599 (score=0.2534) |
| `CITE-019` | novelty-checker | Verified novelty: HYP-004 vs arxiv 2406.18665 (score=0.2559) |
| `CITE-020` | novelty-checker | Verified novelty: HYP-004 vs arxiv 2207.05221 (score=0.2138) |
| `CITE-021` | novelty-checker | Verified novelty: HYP-004 vs arxiv 2302.09664 (score=0.3244) |
| `CITE-022` | novelty-checker | Verified novelty: HYP-004 vs arxiv 2509.25532 (score=0.2825) |
| `CITE-023` | novelty-checker | Verified novelty: HYP-005 vs arxiv 2603.04445 (score=0.2666) |
| `CITE-024` | novelty-checker | Verified novelty: HYP-005 vs arxiv 2308.06077 (score=0.2665) |
| `CITE-025` | novelty-checker | Verified novelty: HYP-005 vs arxiv 2604.07494 (score=0.3110) |
| `CITE-026` | novelty-checker | Verified novelty: HYP-005 vs arxiv 2407.10834 (score=0.2838) |
| `CITE-027` | novelty-checker | Verified novelty: HYP-005 vs arxiv 2409.15518 (score=0.2620) |
| `CITE-028` | novelty-checker | Verified novelty: HYP-007 vs arxiv 2403.12031 (score=0.2542) |
| `CITE-029` | novelty-checker | Verified novelty: HYP-007 vs arxiv 2406.18665 (score=0.3795) |
| `CITE-030` | novelty-checker | Verified novelty: HYP-007 vs arxiv 2410.10347 (score=0.2618) |
| `CITE-031` | novelty-checker | Verified novelty: HYP-008 vs arxiv 2403.12031 (score=0.2584) |
| `CITE-032` | novelty-checker | Verified novelty: HYP-008 vs arxiv 2410.10347 (score=0.2697) |
| `CITE-033` | novelty-checker | Verified novelty: HYP-008 vs arxiv 2603.04445 (score=0.3138) |

## Critique (21)

| id | author | summary |
|----|--------|---------|
| `CRIT-001` | screen-boredom | DistilBERT routing on MMLU already explored (FrugalGPT, RouteLLM); lacks novel mechanism |
| `CRIT-002` | critic | HYP-004 is incremental; combines established techniques with conservative 20% target far below published baselines |
| `CRIT-003` | critic | HYP-005 is a standard model-selection ablation with a foreordained outcome: tautological that 3-tier > 2-tier at some cost point; no novel insight or technique. |
| `CRIT-004` | critic | HYP-003 is a near-duplicate of LIT-011 with incremental syntax-feature elaboration; critical metric mismatch between routing accuracy and cost efficiency |
| `CRIT-005` | screen-boredom | Output-based routing already explored; judge is underspecified and domain-specific; weak baseline comparison; latency not addressed |
| `CRIT-006` | critic | HYP-006 is a direct, low-novelty transplant of established contextual-bandit online learning; predicts modest ≥15pp cost gain in a narrow MMLU→GSM8K shift with oracle reward signal |
| `CRIT-007` | critic | RES-001 validity critique: simulation-only design, trivial sanity gate, and assumed judge ROC limit generalizability of negative result |
| `CRIT-008` | critic | DistilBERT routing on MMLU already explored (FrugalGPT, RouteLLM); Haiku-router baseline weak straw-man; 15% threshold far below published baselines |
| `CRIT-009` | critic | HYP-005 is tautological: 3-tier > 2-tier follows trivially; already proven in literature |
| `CRIT-010` | critic | HYP-003 is near-duplicate of LIT-011 with metric mismatch: predicts routing accuracy instead of cost efficiency |
| `CRIT-011` | critic | Output-conditioned routing already explored; judge too simplistic; cost asymmetry breaks transplant |
| `CRIT-012` | critic | HYP-004 is a narrow optimization of a well-understood technique; Platt scaling is standard calibration, and confidence-based routing is subordinate to stronger approaches |
| `CRIT-013` | critic | HYP-006: low-novelty bandit transplant with unrealistic oracle assumptions; modest gains vs published baselines |
| `CRIT-014` | critic | Batch knapsack optimization is standard; conflates quality prediction (borrowed) with budget allocation (algorithmic); modest ≥20% target; unclear architectural distinction from HYP-004/HYP-006 |
| `CRIT-015` | screen-boredom | HYP-007 is feature-engineering incrementalism: rolling history features add modest complexity without novel insight or strong baseline comparison |
| `CRIT-016` | critic | RES-001 validity: negative result directionally sound but magnitude untrustworthy; simulation-only + assumed judge ROC + no cost-ratio sensitivity |
| `CRIT-017` | critic | RES-002 validity: selective speculation shows real mechanism (+5.93pp) but simulation-only design, fixed judge params, and zone instability undermine precise claims |
| `CRIT-018` | critic | RES-003 validity: knapsack failure is implementation bug (mispriced S→O upgrades), not valid test of batch routing; negative result does not generalize |
| `CRIT-019` | critic | RES-001 validity: structural overhead argument is sound but magnitude unquantifiable from simulation; 3 compounding threats prevent confident rejection of HYP-002 |
| `CRIT-020` | critic | RES-002 validity: positive mechanism (+5.93pp) is real but undecomposed; zone instability, fixed judge, and missing triage-only ablation prevent attribution; CI straddles threshold |
| `CRIT-021` | critic | RES-003 validity: negative result is implementation artifact (mispriced marginal upgrades), not valid test of HYP-008; 75% Opus allocation is pathological proof of bug |

## ExperimentPlan (3)

| id | author | summary |
|----|--------|---------|
| `EXP-001` | experiment-designer | Speculative cascade vs input-feature router on simulated GSM8K (1319 questions): quality-matched cost comparison across 3 seeds |
| `EXP-002` | experiment-designer | Selective speculation: hybrid input-pre-screen + output-verified cascade vs pure input-feature router on simulated GSM8K (3 seeds) |
| `EXP-003` | experiment-designer | Portfolio batch knapsack routing vs independent threshold routing on simulated RouterBench MMLU (3-tier, 1000 queries × 5 batches × 3 seeds) |

## ExperimentResult (3)

| id | author | summary |
|----|--------|---------|
| `RES-001` | experiment-runner | Speculative cascade FAILS HYP-002: -5.72pp vs feature router (threshold >=+8pp); baseline saves 18.9pp vs proposed 13.2pp |
| `RES-002` | experiment-runner | Selective speculation improves over pure input-feature router by +5.93pp mean (3 seeds), but fails pre-registered 8pp threshold; mechanism is positive but insufficient |
| `RES-003` | experiment-runner | Batch knapsack FAILS HYP-008: costs 16.75pp MORE than independent threshold (threshold >=+20% savings); independent router achieves 32.6% savings vs Opus vs batch's 21.6% |

## DraftSection (7)

| id | author | summary |
|----|--------|---------|
| `DRAFT-001` | paper-writer | Paper outline v1: negative/preliminary results in speculative and batch LLM routing |
| `DRAFT-002` | paper-writer | Abstract v1: negative and preliminary results on speculative cascade and batch knapsack LLM routing |
| `DRAFT-003` | paper-writer | Introduction v1: motivates speculative cascade and batch knapsack routing, previews negative results |
| `DRAFT-004` | paper-writer | Related Work v1: input-feature routing, output-conditioned cascades, speculative decoding transplant, multi-tier and batch routing, confidence calibration |
| `DRAFT-005` | paper-writer | Method v1: simulation framework, three experiment designs (speculative cascade, selective speculation, batch knapsack), baselines, and evaluation protocol |
| `DRAFT-006` | paper-writer | Experiments v1: results for speculative cascade, selective speculation, and batch knapsack routing with validity analysis |
| `DRAFT-007` | paper-writer | Discussion v1: interprets negative/preliminary results, structural overhead analysis, methodological lessons, limitations, and future directions |
