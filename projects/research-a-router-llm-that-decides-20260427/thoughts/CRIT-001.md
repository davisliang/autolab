---
{
  "id": "CRIT-001",
  "type": "Critique",
  "created_at": "2026-04-27T04:29:23+00:00",
  "parent_ids": [
    "HYP-001"
  ],
  "author": "screen-boredom",
  "summary": "DistilBERT routing on MMLU already explored (FrugalGPT, RouteLLM); lacks novel mechanism",
  "body_path": "thoughts/CRIT-001.md",
  "target_id": "HYP-001",
  "mode": "boredom",
  "severity": "high",
  "concerns": [
    "DistilBERT routing extensively explored in FrugalGPT (LIT-013) and RouteLLM (LIT-008, LIT-016)",
    "HYP-001 proposes standard supervised fine-tuning on MMLU oracle labels",
    "No novel routing signal, training procedure, or architectural innovation",
    "15% efficiency gain threshold is modest vs FrugalGPT's 98% cost reduction",
    "Straightforward application of existing technique to a new dataset, not a research contribution"
  ],
  "proposed_fix": "Park HYP-001. To retain, justify why MMLU oracle + DistilBERT differs from FrugalGPT, or pivot to novel routing signals (embeddings + confidence bounds, production-log datasets, etc.)"
}
---

## Boredom Analysis: HYP-001

### Finding
DistilBERT-based text classification for routing between model sizes is extensively explored in prior literature and lacks novel mechanism.

### Evidence
- **LIT-013 (FrugalGPT)**: Explicitly uses DistilBERT scoring for cascade routing, achieves 98% cost reduction vs GPT-4
- **LIT-008, LIT-016 (RouteLLM)**: BERT-style routers trained on preference data, 2x+ cost savings on MMLU
- **LIT-014 (DeBERTa router)**: Transformer-based classifier for routing, 40% fewer large-model calls
- **LIT-009 (Hybrid LLM)**: BERT-based binary router, 40% reduction with <1% quality drop

### Critique
HYP-001 proposes training DistilBERT on MMLU oracle labels (cheapest model ≥90% Opus quality per query). This is a straightforward supervised learning baseline. The novelty claim—"more cost-efficient than Haiku-as-router"—is not novel; it's an obvious improvement over any approach that runs inference on every query.

The 15% pre-registered efficiency gain is also modest: FrugalGPT reports 98% cost reduction, implying gains far larger than 15%. The hypothesis presents no new routing signal (just query text), no new training procedure (standard fine-tuning), and no architectural innovation.

This is "reproduce existing technique on a different dataset," not a research contribution. Better: propose a novel signal (e.g., query embeddings + confidence-bound reasoning) or dataset (e.g., production logs rather than benchmark data).

### Recommendation
Park HYP-001. If retained after user review, clarify what is novel relative to FrugalGPT's DistilBERT cascade.
