# Thread index

_53 artifacts_  

## Idea (1)

| id | author | summary |
|----|--------|---------|
| `IDEA-001` | orchestrator | research a router LLM that decides whether to call Haiku, Sonnet, or Opus based on query complexity. Build something that goes beyond what is already existing and outperforms the baselines that already exist. |

## Hypothesis (6)

| id | author | summary |
|----|--------|---------|
| `HYP-001` | idea-expander | Multi-signal feature router (token count + lexical diversity + syntactic depth + task-type embedding) achieves ≥85% routing accuracy, beating length-only heuristics. |
| `HYP-002` | idea-expander | Confidence-cascade routing (cheap-model-first, escalate on low confidence) achieves cost-normalized quality ≥15% better than a flat upfront router on diverse benchmarks. |
| `HYP-003` | idea-expander | [CROSS-DOMAIN TRANSPLANT from adaptive bitrate streaming] BOLA-inspired online-adaptive router limits quality degradation to <3% within 50 queries after an abrupt domain shift. |
| `HYP-004` | idea-expander | Self-supervised routing via output-entropy labeling closes within 5pp routing accuracy of fully-supervised routing, eliminating costly human-labeled difficulty annotation. |
| `HYP-005` | idea-expander | Latency-SLA-aware router that incorporates EWMA latency estimates per tier reduces P95 latency ≥25% vs. cost-only router at matched mean quality. |
| `HYP-006` | idea-expander | Conversation-aware router conditioning on dialogue complexity trajectory reduces unnecessary Opus escalations ≥20% vs. per-query router on MT-Bench without quality loss. |

## LitFinding (22)

| id | author | summary |
|----|--------|---------|
| `LIT-001` | literature-scout | Kadavath et al. (Anthropic) show output entropy H(A\|Q) over sampled completions discriminates questions a model answers correctly from those it fails—directly validating HYP-004's entropy-labeling mechanism, but with an important caveat: AUROC trend is negative on HumanEval as models scale. |
| `LIT-002` | literature-scout | Kuhn et al. (Oxford) introduce Semantic Entropy—entropy over clustered meanings rather than raw token sequences—which outperforms raw entropy for predicting LLM accuracy on QA, directly bearing on HYP-004's token-level entropy labeling quality. |
| `LIT-003` | literature-scout | Wang et al. (Google) show that sampling diverse reasoning paths and taking majority vote (self-consistency) robustly improves CoT accuracy—the consistency/agreement signal across samples is an unsupervised, label-free proxy for difficulty that underpins HYP-004's entropy approach. |
| `LIT-004` | literature-scout | BOLA uses Lyapunov optimization for near-optimal adaptive bitrate streaming, the direct algorithmic source for HYP-003. |
| `LIT-005` | literature-scout | FrugalGPT shows LLM cascade cuts cost 98% via static trained thresholds, but requires same-distribution training data — vulnerable to domain shift. |
| `LIT-006` | literature-scout | Chen et al. (Stanford) propose FrugalGPT—an LLM cascade that uses a learned generation-scoring function to decide when to escalate from cheap to expensive models—providing a cost-reduction baseline and the generation-scoring primitive that HYP-004's entropy labeler would replace. |
| `LIT-007` | literature-scout | Hybrid LLM proposes quality-gap-aware router achieving 40% fewer large-model calls; routing threshold is fixed post-training with no online adaptation. |
| `LIT-008` | literature-scout | RouteLLM trains preference-data-based routers achieving >2x cost savings with strong OOD generalization, but all training is offline with no online adaptation. |
| `LIT-009` | literature-scout | Ong et al. (UC Berkeley/Anyscale) introduce RouteLLM—a framework for learning routers from human preference data that achieves >2x cost savings with minimal quality loss—establishing the state-of-the-art supervised routing baseline that HYP-004's self-supervised approach aims to match within 5pp. |
| `LIT-010` | literature-scout | LLM-Blender shows no single LLM dominates (best wins only 21% of cases), motivating adaptive per-query tier selection across domain shifts. |
| `LIT-011` | literature-scout | FrugalGPT introduces LLM cascade with learned scoring function: matches GPT-4 accuracy with 98% cost reduction. |
| `LIT-012` | literature-scout | RouteLLM learns preference-data-based routers, reducing cost >2x at parity quality; single-query design avoids cascade latency. |
| `LIT-013` | literature-scout | CALM uses calibrated per-token confidence for early exit in LLMs, achieving 3x speedup with provable sequence-level quality guarantees. |
| `LIT-014` | literature-scout | Kadavath et al. (Anthropic) show large LMs are well-calibrated on MC/T-F; P(True) self-evaluation distinguishes correct from incorrect samples. |
| `LIT-015` | literature-scout | Self-Consistency: sampling diverse CoT paths + majority vote boosts GSM8K by +17.9%; answer agreement across paths is a calibration-free confidence proxy. |
| `LIT-016` | literature-scout | Speculative decoding: cheap draft model + expensive target model for 2-3x speedup; token acceptance rate is structurally analogous to cascade escalation rate. |
| `LIT-017` | literature-scout | FrugalGPT: LLM cascade achieves 98% cost reduction via output-conditional scoring; pre-generation query-feature routing is unexplored. |
| `LIT-018` | literature-scout | RouteLLM: BERT router trained on human preference data achieves >2x cost savings on MMLU/MT-Bench; uses dense embeddings not interpretable features. |
| `LIT-019` | literature-scout | Hybrid LLM: DeBERTa quality-gap router achieves 40% fewer large-model calls at <1% quality drop; most architecturally similar prior work to HYP-001. |
| `LIT-020` | literature-scout | AutoMix: POMDP router using few-shot self-verification achieves >50% cost reduction; output-conditional cascade contrasting with HYP-001 pre-generation approach. |
| `LIT-021` | literature-scout | RouterBench: First standardized routing benchmark with 405k inference outcomes across 11 LLMs/8 datasets; validates simple supervised classifiers are competitive. |
| `LIT-022` | literature-scout | LLM-Blender: PairRanker shows best LLM wins only 21% of examples, empirically motivating per-query routing; ensemble approach calls all N models unlike HYP-001. |

## Citation (14)

| id | author | summary |
|----|--------|---------|
| `CITE-001` | novelty-checker | HYP-001 vs RouteLLM: novelty score 0.2562 |
| `CITE-002` | novelty-checker | HYP-001 vs Hybrid LLM: novelty score 0.2854 |
| `CITE-003` | novelty-checker | HYP-001 vs RouterBench: novelty score 0.2532 |
| `CITE-004` | novelty-checker | HYP-002 vs FrugalGPT: novelty score 0.2863 |
| `CITE-005` | novelty-checker | HYP-002 vs AutoMix: novelty score 0.2379 |
| `CITE-006` | novelty-checker | HYP-003 vs BOLA: novelty score 0.2733 |
| `CITE-007` | novelty-checker | HYP-003 vs Speculative decoding: novelty score 0.2879 |
| `CITE-008` | novelty-checker | HYP-004 vs Kadavath entropy: novelty score 0.2126 |
| `CITE-009` | novelty-checker | HYP-004 vs Semantic Entropy: novelty score 0.316 |
| `CITE-010` | novelty-checker | HYP-004 vs Self-consistency: novelty score 0.2978 |
| `CITE-011` | novelty-checker | HYP-005 vs RouteLLM: novelty score 0.3065 |
| `CITE-012` | novelty-checker | HYP-005 vs RouterBench: novelty score 0.2376 |
| `CITE-013` | novelty-checker | HYP-006 vs RouteLLM: novelty score 0.2669 |
| `CITE-014` | novelty-checker | HYP-006 vs FrugalGPT: novelty score 0.3063 |

## Critique (6)

| id | author | summary |
|----|--------|---------|
| `CRIT-001` | critic | EWMA latency tracking is engineering-focused; core novelty is incremental. |
| `CRIT-002` | critic | HYP-002 applies established cascading + confidence calibration without algorithmic novelty; high boredom, candidate for parking. |
| `CRIT-003` | critic | HYP-003 mechanically straightforward cross-domain transplant; online-adaptation novelty offset by trivial variable substitution and narrow prediction scope |
| `CRIT-004` | critic | HYP-001 is redundant with Hybrid LLM; no novel mechanism or feature signal |
| `CRIT-005` | critic | HYP-006 feature-engineering incremental on narrow benchmark; statistical power insufficient |
| `CRIT-006` | critic | HYP-004 applies a known entropy labeling mechanism to routing with under-specified conceptual link and generous success threshold |

## ExperimentPlan (4)

| id | author | summary |
|----|--------|---------|
| `EXP-001` | experiment-designer | Conversation-aware vs per-query LightGBM router on MT-Bench multi-turn: measure unnecessary escalation reduction with bootstrap CI |
| `EXP-002` | experiment-designer | BOLA-router vs static-threshold baseline under abrupt domain shift on simulated 3-tier routing |
| `EXP-003` | experiment-designer | Latency-SLA-aware EWMA router vs cost-only baseline on simulated 3-tier routing with P95 latency as primary metric |
| `EXP-004` | experiment-designer | Self-supervised entropy-router vs supervised router on synthetic MMLU+GSM8K+HumanEval proxy (LightGBM, 3 seeds, baseline=supervised labels) |
