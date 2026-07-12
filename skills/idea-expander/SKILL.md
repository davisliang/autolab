---
name: idea-expander
description: Expand a seed Idea into 3-5 falsifiable Hypotheses with pre-registered numeric predictions. Includes cross-domain transplant ideation and negative-space gap-filling. Use when the orchestrator runs the `expand` or `gap-fill` phase.
---

# idea-expander

## Objective

Take a seed `Idea` (in expand phase) or the `LitFinding` set (in gap-fill phase) and produce `Hypothesis` artifacts. Each hypothesis must be falsifiable and locally testable, and ship with a pre-registered prediction — but the *idea* is not the metric. The metric is only how you will _test_ the idea; the idea itself is a claim about how something works and why anyone should care.

**Fight myopia first.** The recurring failure of this lab is not that ideas are wrong — it is that they are *small*: a single mechanism, checked with a single number, on a toy that answers a question nobody was asking. A clean pre-registered prediction on a narrow probe is still a myopic paper. Before you emit anything, name — in the body of every hypothesis — the **bigger question** it is a probe of, and the **stakes**: what changes in how the field thinks or builds if the answer is yes. If you cannot state a bigger question and non-trivial stakes, the hypothesis is not ready; enlarge it or throw it out. A hypothesis is the smallest testable *slice of a large question*, not a replacement for one.

## Modes

The orchestrator's prompt names one of:

- `mode=expand` — operate on a single `Idea`. Output 3-5 `Hypothesis` rows.
- `mode=gap-fill` — operate on the existing `Idea` + `LitFinding` set. Output 1-2 `Hypothesis` rows targeting a question conspicuously absent from the literature.

## Inputs

- `mode=expand`: read `thoughts/IDEA-<id>.md`
- `mode=gap-fill`: read `thoughts/IDEA-<id>.md` + every `thoughts/LIT-*.md` listed in `thread/INDEX.md` under `LitFinding`

## Outputs

`Hypothesis` artifacts via `python -m autolab.append_artifact`. Required fields:
- `claim` — one sentence, in **plain language** (see "Write it like an undergrad" below). State what you think is true, not the machinery used to test it.
- `plain_summary` — **required.** 2–4 sentences a smart undergrad who has taken one ML course could follow, with **zero undefined jargon**. Cover, in order: (1) what we think is true, in everyday words; (2) why anyone should care — what changes if it's true; (3) how we'll check it, in one plain sentence. This is the FIRST thing the human sees at review, so it must stand on its own without the claim or the metric line.
- `prediction_metric` — e.g. `val_accuracy`, `val_loss`, `bits_per_byte`, `wall_seconds`
- `prediction_threshold` — the pre-registered decision boundary. Prefer a number (e.g. `0.5` for "≥0.5pp gain") when a scalar is the *honest* summary of the claim. When forcing the claim into a single scalar would distort the science — the real prediction is relational ("monotone decrease with depth"), structural ("the effect survives control X but not control Y"), or a shape ("crossover at some scale") — set `prediction_threshold` to the string form of that falsifiable condition instead, and still name the observable that would break it. Do not invent a fake number to satisfy the field.
- `prediction_direction` — `"greater"` | `"less"` | `"equal-within"` (or `"relational"` when the prediction is not a one-sided scalar)
- `prerequisites` — list of LIT/IDEA ids that motivate it

Record in the markdown body (not required as JSON fields, but expected in prose):
- `bigger_question` — the large, consequential question this hypothesis is one probe of
- `stakes` — what changes in how the field thinks or builds if the claim holds; who would act differently

## Write it like an undergrad

The human reviewing these hypotheses is smart but is NOT a specialist in every subfield you draw from. Every human-facing string — `claim`, `plain_summary`, `bigger_question`, `stakes` — must be readable by a second-year undergrad who has taken one ML course. This is not optional polish; a hypothesis nobody can parse cannot be reviewed, so it is a bad hypothesis.

Rules:
- **No undefined jargon.** If you must use a term of art, define it in the same sentence in plain words. Prefer the plain word outright: "scoreboard of which model got which question right", not "query-by-model score matrix".
- **Lead with the point, not the method.** Say what you believe about the world before you say how you'll measure it. SVD, spectral energy, residual rank — these are *tools*, they belong in the metric line, not in the plain summary.
- **One idea per sentence.** If a sentence has three clauses and two symbols, split it.
- **Always answer "so what?"** in words a practitioner would nod at.

The technical precision still lives in `prediction_metric` / `prediction_threshold` / `prediction_direction` and the "breaking observable" — that is where reviewers who want the rigor will look. Keep those exact. Do NOT dumb those down. The plain fields are the front door; the metric fields are the fine print.

**Before (too technical — do NOT write claims like this):**
> The query-by-model score matrix is dominated by a single general-capability factor, yet nearly all achievable oracle routing gain over the best single model is carried by the low-energy residual beyond rank-1, making residual spectral energy a measurable ceiling on any router.

**After (`claim`):**
> Picking the best AI model per question can only beat the single best model by exploiting the rare cases where a weaker model happens to win — and how many such cases exist is something we can measure up front.

**After (`plain_summary`):**
> Say you have several AI models and a pile of questions, and a scoreboard of which model got each question right. Most of that scoreboard just reflects one thing — some models are generally smarter than others. A "router" that picks the best model per question can only do better than always using the single best model by catching the leftover cases where a weaker model wins. We think those leftover cases set a hard ceiling on how good any router can be, and that ceiling is measurable before you build the router. Why it matters: if the leftovers are tiny, routing isn't worth the engineering; if they're big, it is. We check by removing the leftovers and seeing whether the routing advantage disappears.

## Tools

- `Read`, `Grep` — to inspect thread + thoughts + papers
- `Bash` — to invoke `python -m autolab.append_artifact` for emission
- `WebFetch` — only via the `huggingface-papers` skill if you need quick paper context

## Recommended model

`fable-5`

## Wildness bar (applies in BOTH modes)

The orchestrator may inject a "WILDNESS BAR" block into your prompt. Every Hypothesis you emit MUST satisfy at least one Wildness Ticket and name it in the body:

- **W1 — NON-ML cross-domain transplant.** Source must be neuroscience, biology, physics, control theory, evolutionary theory, economics, linguistics, signal processing, statistics-beyond-ML, chemistry, or statistical mechanics. RL→supervised, vision→NLP, optimization→architecture do **NOT** count — they are too close.
- **W2 — Contradicts a textbook claim or widely-held assumption.** State the textbook claim verbatim, then state your counter-claim.
- **W3 — Measures something nobody has measured at meaningful scale.** Say why the measurement was missing.
- **W4 — Regime swap.** Predict what changes when scale, data quality, modality, or compute is 100× or 0.01× the standard.

**Wildness is necessary but not sufficient — the ticket buys novelty, not consequence.** A cross-domain transplant (W1) that ends in a single-metric toy test is *myopia wearing a costume*: it looks wild because the source field is exotic, but the result would still change nothing. Every hypothesis must clear a second bar on top of its ticket:

- **Consequence.** If the prediction holds, at least one specific person — a practitioner, a theorist, the designer of the next system — does something *differently*. Name them and name the change. "It would be interesting" is not consequence.
- **Line of sight.** The toy/first experiment must have a credible path to something bigger. If the honest answer to "and then what?" is "nothing — this is where it ends," the idea is a dead end regardless of how clean the number is.

**Reject-yourself examples** (do NOT emit these, no matter how clean the prediction or how exotic the source field):
- "Test if X works on Y" (just a measurement, no insight)
- "Try variant of method M" (incrementalism)
- "Replicate paper P with smaller model" (replication, not novelty)
- "Combine A and B" without a *mechanistic* reason the combination matters
- Anything a sharp PhD student would predict the outcome of in 30 seconds
- **Wild-but-myopic:** imports a striking analogy from another field but only ever tests one scalar on one toy, with no bigger question and nobody who would act on the answer. Exotic framing does not rescue a small idea.

If the orchestrator retreats with an "IDEA-CYCLE RETREAT CONTEXT" block, the previous batch was judged boring. Read the parking-lot reasons and propose ideas that are *bigger and more consequential* — not just more exotic, and never minor variations.

If the RUN HISTORY contains a **USER FEEDBACK / DIRECTION** entry, treat it as the highest-priority steer: the human running the lab has told you which direction to take the ideas or has asked for a fresh batch. Honor that direction explicitly in this batch before applying any other heuristic.

## Procedure (mode=expand)

1. Read the seed `Idea`. Identify: dataset, model class, claim space, compute regime.
2. Generate 3 in-domain hypotheses, each satisfying at least one Wildness Ticket (W2/W3/W4 are the most achievable in-domain).
3. **Mandatory W1 ticket**: generate at least 1 hypothesis that imports a technique from a NON-ML field (per the list above). State the source field and the mechanistic analogy explicitly in the body.
4. For each hypothesis, write a one-sentence plain-language `claim`, a plain-language `plain_summary` (see "Write it like an undergrad"), a `prediction_metric/threshold/direction` (numeric threshold when a scalar is the honest summary; a falsifiable relational/structural condition otherwise), name the wildness ticket(s) it satisfies, and a rationale referencing IDEA-<id> by reference (no requoting). The rationale MUST include the `bigger_question` it probes and the `stakes` — who acts differently if it holds — both stated in plain language.
5. Verify each prediction is locally testable in <30 minutes on Apple Silicon. If not, scale down the *test* — never the ambition. Keep the bigger question; shrink only the first probe of it. If even the smallest honest probe won't fit, drop the hypothesis rather than shrinking the question until it's trivial.
6. Emit each via `python -m autolab.append_artifact --type Hypothesis --parent IDEA-<id> --summary "<claim>" --field plain_summary="<plain-language explanation>" --field prediction_metric=<m> --field prediction_threshold=<n> --field prediction_direction=<dir>`. The tool prints the new id; capture it.

## Procedure (mode=gap-fill)

1. Read the `Idea` and every `LitFinding` body.
2. Build a 1-paragraph map of what the literature *has* covered: methods used, datasets used, claims made.
3. Identify what is conspicuously *missing* — a question the LIT set sets up but no paper answers, or an obvious comparison no one has run.
4. Emit 1-2 `Hypothesis` rows targeting that gap, with the same required fields as expand mode. In the rationale, name explicitly which papers set up the question and *why* it remains unanswered.

## Boundaries

- **Do not invoke other skills directly.** Return to the orchestrator after appending.
- **Do not run experiments.** That is `experiment-runner`'s job.
- **Do not make claims requiring data you don't have.**
- **Do not propose hypotheses that require >30 min of compute** on a single Apple Silicon machine. This caps the *test*, not the *question* — a 30-minute probe of a large question is the goal; a 30-minute question is the failure mode.
- Every hypothesis MUST have a falsifiable `prediction_threshold` (numeric when honest, a relational/structural condition otherwise), a plain-language `plain_summary` a non-specialist can follow, AND a stated bigger question with stakes. Hypotheses missing a falsifiable prediction, missing a readable plain summary, or that are myopic (no bigger question, nobody who would act on the answer), will be parked at `screen`.

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
  --field plain_summary="When training a small neural net, every layer usually shares one learning-rate schedule. We borrow a trick from reinforcement learning: adjust each layer's step size based on how much its outputs are already moving, so fast-moving layers slow down. We think this small change makes MNIST training a bit more accurate. If it works, it's a cheap, general tweak anyone training small nets could adopt. We check by comparing final validation accuracy against plain uniform learning rates over 3 runs." \
  --field prediction_metric=val_accuracy \
  --field prediction_threshold=0.3 \
  --field prediction_direction=greater \
  --field prerequisites=IDEA-001 \
  --body-from-stdin
```
