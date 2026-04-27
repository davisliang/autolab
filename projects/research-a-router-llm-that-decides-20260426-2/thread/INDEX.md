# Thread index

_6 artifacts_  

## Idea (1)

| id | author | summary |
|----|--------|---------|
| `IDEA-001` | orchestrator | research a router LLM that decides whether to call Haiku, Sonnet, or Opus based on query complexity. Build something that goes beyond what is already existing and outperforms the baselines that already exist. |

## Hypothesis (5)

| id | author | summary |
|----|--------|---------|
| `HYP-001` | idea-expander | Probing-classifier routing: lightweight MLP on frozen embeddings achieves ≥5% cost reduction at iso-quality vs always-Sonnet |
| `HYP-002` | idea-expander | [CROSS-DOMAIN] Speculative cascade routing (transplant from speculative decoding): draft-then-verify achieves ≥10% cost reduction vs always-Sonnet at ≤1% quality drop |
| `HYP-003` | idea-expander | Online contextual bandit router (LinUCB) achieves ≥3pp better routing accuracy on OOD queries vs static trained classifier |
| `HYP-004` | idea-expander | Multi-signal feature fusion (syntax depth + NER count + CoT indicators + domain embedding) improves routing F1 by ≥4pp over embedding-only baseline |
| `HYP-005` | idea-expander | Utility-maximizing router with learned quality-cost tradeoff curve achieves Pareto dominance at ≥60% of tested budget levels vs fixed-threshold routing |
