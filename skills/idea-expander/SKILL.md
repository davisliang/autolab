---
name: idea-expander
description: Expand a seed Idea into 3-5 falsifiable Hypotheses with pre-registered numeric predictions. Includes cross-domain transplant ideation and negative-space gap-filling. Use when the orchestrator runs the `expand` or `gap-fill` phase.
---

# idea-expander

## Objective

Take a seed `Idea` (in expand phase) or the `LitFinding` set (in gap-fill phase) and produce `Hypothesis` artifacts. Each hypothesis must be falsifiable, locally testable, and ship with a pre-registered numeric prediction.

## Modes

The orchestrator's prompt names one of:

- `mode=expand` — operate on a single `Idea`. Output 3-5 `Hypothesis` rows.
- `mode=gap-fill` — operate on the existing `Idea` + `LitFinding` set. Output 1-2 `Hypothesis` rows targeting a question conspicuously absent from the literature.

## Inputs

- `mode=expand`: read `thoughts/IDEA-<id>.md`
- `mode=gap-fill`: read `thoughts/IDEA-<id>.md` + every `thoughts/LIT-*.md` listed in `thread/INDEX.md` under `LitFinding`

## Outputs

`Hypothesis` artifacts via `python -m autolab.append_artifact`. Required fields:
- `claim` — one sentence
- `prediction_metric` — e.g. `val_accuracy`, `val_loss`, `bits_per_byte`, `wall_seconds`
- `prediction_threshold` — numeric (e.g. `0.5` for "≥0.5pp gain")
- `prediction_direction` — `"greater"` | `"less"` | `"equal-within"`
- `prerequisites` — list of LIT/IDEA ids that motivate it

## Tools

- `Read`, `Grep` — to inspect thread + thoughts + papers
- `Bash` — to invoke `python -m autolab.append_artifact` for emission
- `WebFetch` — only via the `huggingface-papers` skill if you need quick paper context

## Recommended model

`sonnet-4-6`

## Wildness bar (applies in BOTH modes)

The orchestrator may inject a "WILDNESS BAR" block into your prompt. Every Hypothesis you emit MUST satisfy at least one Wildness Ticket and name it in the body:

- **W1 — NON-ML cross-domain transplant.** Source must be neuroscience, biology, physics, control theory, evolutionary theory, economics, linguistics, signal processing, statistics-beyond-ML, chemistry, or statistical mechanics. RL→supervised, vision→NLP, optimization→architecture do **NOT** count — they are too close.
- **W2 — Contradicts a textbook claim or widely-held assumption.** State the textbook claim verbatim, then state your counter-claim.
- **W3 — Measures something nobody has measured at meaningful scale.** Say why the measurement was missing.
- **W4 — Regime swap.** Predict what changes when scale, data quality, modality, or compute is 100× or 0.01× the standard.

**Reject-yourself examples** (do NOT emit these, no matter how clean the prediction):
- "Test if X works on Y" (just a measurement, no insight)
- "Try variant of method M" (incrementalism)
- "Replicate paper P with smaller model" (replication, not novelty)
- "Combine A and B" without a *mechanistic* reason the combination matters
- Anything a sharp PhD student would predict the outcome of in 30 seconds

If the orchestrator retreats with an "IDEA-CYCLE RETREAT CONTEXT" block, the previous batch was judged boring. Read the parking-lot reasons and propose substantially wilder ideas — not minor variations.

## Procedure (mode=expand)

1. Read the seed `Idea`. Identify: dataset, model class, claim space, compute regime.
2. Generate 3 in-domain hypotheses, each satisfying at least one Wildness Ticket (W2/W3/W4 are the most achievable in-domain).
3. **Mandatory W1 ticket**: generate at least 1 hypothesis that imports a technique from a NON-ML field (per the list above). State the source field and the mechanistic analogy explicitly in the body.
4. For each hypothesis, write a one-sentence `claim`, a numeric `prediction_metric/threshold/direction`, name the wildness ticket(s) it satisfies, and a 2-3 sentence rationale referencing IDEA-<id> by reference (no requoting).
5. Verify each prediction is locally testable in <30 minutes on Apple Silicon. If not, scale down or drop.
6. Emit each via `python -m autolab.append_artifact --type Hypothesis --parent IDEA-<id> --summary "<claim>" --field prediction_metric=<m> --field prediction_threshold=<n> --field prediction_direction=<dir>`. The tool prints the new id; capture it.

## Procedure (mode=gap-fill)

1. Read the `Idea` and every `LitFinding` body.
2. Build a 1-paragraph map of what the literature *has* covered: methods used, datasets used, claims made.
3. Identify what is conspicuously *missing* — a question the LIT set sets up but no paper answers, or an obvious comparison no one has run.
4. Emit 1-2 `Hypothesis` rows targeting that gap, with the same required fields as expand mode. In the rationale, name explicitly which papers set up the question and *why* it remains unanswered.

## Boundaries

- **Do not invoke other skills directly.** Return to the orchestrator after appending.
- **Do not run experiments.** That is `experiment-runner`'s job.
- **Do not make claims requiring data you don't have.**
- **Do not propose hypotheses that require >30 min of compute** on a single Apple Silicon machine.
- Every hypothesis MUST have a numeric `prediction_threshold`. Hypotheses missing this will be rejected at `screen`.

## Stdout contract

End with one line:
```
phase=<expand|gap-fill> status=ok new_ids=HYP-001,HYP-002,...
```

## Worked example (cross-domain transplant)

Seed: "investigate whether layer-wise learning rates help small MLPs on MNIST".

Cross-domain transplant: import **trust-region scaling** from RL/PPO — scale per-layer LR by a clipped ratio of pre-update vs. post-update activation norms. Source field: RL policy optimization. Prediction: `val_accuracy` greater by `0.3` pp vs. uniform LR over 3 seeds.

Append:
```
python -m autolab.append_artifact --type Hypothesis \
  --parent IDEA-001 \
  --author idea-expander \
  --summary "Trust-region-style per-layer LR scaling outperforms uniform LR on MNIST MLPs" \
  --field prediction_metric=val_accuracy \
  --field prediction_threshold=0.3 \
  --field prediction_direction=greater \
  --field prerequisites=IDEA-001 \
  --body-from-stdin
```
