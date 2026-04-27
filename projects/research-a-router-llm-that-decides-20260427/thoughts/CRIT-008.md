---
{
  "id": "CRIT-008",
  "type": "Critique",
  "created_at": "2026-04-27T04:58:57+00:00",
  "parent_ids": [
    "HYP-001"
  ],
  "author": "critic",
  "summary": "DistilBERT routing on MMLU already explored (FrugalGPT, RouteLLM); Haiku-router baseline weak straw-man; 15% threshold far below published baselines",
  "body_path": "thoughts/CRIT-008.md",
  "target_id": "HYP-001",
  "mode": "boredom",
  "severity": "high"
}
---

## Boredom Assessment: HIGH

HYP-001 proposes a distilbert-based text classifier to route Haiku/Sonnet/Opus with ≥15% cost-efficiency gain vs. Haiku-as-router on MMLU.

### Why This Is Boring

**1. Core mechanism is thoroughly published.** DistilBERT-based routing is not novel:
   - **FrugalGPT** (LIT-006, LIT-013): Uses DistilBERT scoring; achieves 98% cost reduction vs. GPT-4
   - **RouteLLM** (LIT-008, LIT-016): BERT/DeBERTa routers on MMLU; 2x+ cost savings
   - **Hybrid LLM** (LIT-009): BERT-based binary router; 40% reduction in large-model calls
   - **DeBERTa routers** (LIT-014): 40% fewer large-model calls at matched quality

**2. Baseline is a weak straw-man.** Comparing against "Haiku-as-router":
   - LIT-032 explicitly shows: "LLM router fails latency gate; SLMs achieve zero-marginal-cost routing"
   - LIT-036: "Offline classifiers preferred because LLM router has unacceptable latency overhead"
   - A known-to-be-inferior baseline is not a novelty contribution

**3. Conservative threshold hides incremental work.** The ≥15% improvement is far below published results:
   - FrugalGPT: 98% cost reduction
   - RouteLLM: 2x (200% relative)
   - Hybrid LLM: 40% reduction
   - A 15% target signals the authors know the approach is well-trodden and are hedging with a weak goal

**4. No novel mechanism.** Vanilla DistilBERT fine-tuning on labeled pairs with standard threshold selection and routine evaluation—no technical innovation.

### Novelty Collision
Directly collides with **LIT-008** (RouteLLM): "BERT-style router on human preference data achieves 2x+ cost savings on MMLU; most direct prior-art comparison to HYP-001."

### Recommendation
**Park HYP-001.** The core contribution—pre-trained text classifier for model routing—is established prior art across multiple papers. The conservative 15% threshold and weak Haiku-as-router baseline obscure the incremental nature of this work. Running this would likely reproduce known results without advancing the field.
