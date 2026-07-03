---
name: thought-experimenter
description: Roll out a thought experiment on a deliberate toy problem for a surviving Hypothesis BEFORE any scalability is contemplated. Stress-test the mechanism mentally, predict the toy-scale outcome, name how it could fail, and only then sketch the path to an informative (non-toy) experiment. Use when the orchestrator runs the `thought-experiment` phase.
---

# thought-experimenter

## Objective

For one surviving `Hypothesis`, reason your way through a **toy problem** — the
smallest, most transparent setting in which the hypothesized mechanism either
manifests or it doesn't. Roll the thought experiment forward step by step, in
your head, with no compute. Decide whether the mechanism is even coherent
*before* anyone spends a GPU-hour. Only after the toy rollout do you contemplate
scale.

This phase exists to kill three recurring failure modes:
- experiments that "don't make sense" because nobody checked the mechanism first;
- defaulting to an uninformative benchmark (MNIST, a 2-layer MLP) because it was
  the path of least resistance rather than the *minimal probe of the claim*;
- contemplating scale and engineering before establishing that the effect exists
  in principle at all.

A toy problem here is a **reasoning instrument**, not the final experiment. It
should be chosen so that *if the mechanism is real, the toy problem reveals it,
and if the mechanism is fake, the toy problem exposes that too.* MNIST is almost
never that instrument — pick the setting the claim is actually about.

## Inputs

The orchestrator's prompt names one `Hypothesis` (`HYP-<id>`). Read:
- `thoughts/HYP-<id>.md` — the claim, its pre-registered prediction, and the
  wildness ticket it satisfies.
- Any `LitFinding` bodies linked via `parent_ids`, for context on what is known.

Do **not** read every artifact in the project. Stay focused on this one claim.

## Procedure

1. **Restate the mechanism in one sentence.** Strip the jargon. What, physically
   or mathematically, is supposed to happen, and why would it?
2. **Design the toy problem.** Choose the minimal setting that isolates the
   mechanism — the fewest moving parts in which the claimed effect must appear if
   it is real. State the data, the model, the quantity you would watch, and the
   single comparison that decides the question. Justify *why this setting probes
   the claim* (not just that it is small). If you reach for a stock benchmark,
   write one sentence on why it is the right probe; if you can't, pick something
   else.
3. **Roll the experiment forward in your head.** Walk through what happens step by
   step under the hypothesis, then under the null. Where do the two trajectories
   diverge, and what observable separates them? Be concrete about magnitudes, not
   just direction.
4. **Name the failure modes.** List the ways the toy result could mislead — a
   confound, a degenerate solution, an effect that exists only at toy scale and
   vanishes (or only appears) at scale. If a sharp colleague would predict the
   toy outcome in 30 seconds, say so.
5. **Render a verdict** on whether a real experiment is worth designing:
   - `promising` — the rollout supports the mechanism; the toy problem would
     show it; proceed to design.
   - `inconclusive` — the rollout is genuinely uncertain; the toy problem is
     worth running precisely because the answer isn't obvious. Proceed.
   - `refuted` — the rollout shows the mechanism cannot work, is confounded
     beyond rescue, or the outcome is trivially predictable. Do not design;
     the orchestrator will park the hypothesis with your reasoning attached.
6. **Only now, contemplate scalability — and consequence.** If (and only if) the
   verdict is `promising` or `inconclusive`, sketch the path *out* of the toy
   problem: what the first informative (non-toy) experiment looks like, what would
   have to hold for the toy result to survive contact with realistic
   scale/data/modality, and the cheapest observation that would break the claim at
   scale. Name, in one sentence, the **consequential claim the toy is a proxy
   for** — the thing someone would actually act on if the full result held. If the
   only honest path forward is "a slightly bigger version of the same toy" with no
   line of sight to anything anyone would build on, say so plainly and lean toward
   `refuted` (a myopic dead end), even when the mechanism itself is coherent: a
   coherent mechanism that leads nowhere is not worth a GPU-hour. This is what the
   `design` phase builds on — keep it concrete and a single step beyond the toy,
   not a research program.

## Outputs

One `ThoughtExperiment` artifact via `python -m autolab.append_artifact`.
Required fields:

- `hypothesis_id` — the `HYP-<id>` this rolls out
- `toy_problem` — one sentence naming the minimal setting and the deciding comparison
- `predicted_outcome` — what the rollout predicts at toy scale, with a rough magnitude
- `mechanism` — the de-jargoned one-sentence reason the effect would occur
- `verdict` — `"promising"` | `"inconclusive"` | `"refuted"`
- `scalability_note` — the single concrete step from toy problem toward an
  informative experiment, ending with the one-sentence consequential claim the
  toy is a proxy for (write `"n/a — refuted"` when the verdict is `refuted`)

Put the full step-by-step rollout, the null trajectory, and the failure-mode
list in the markdown body via `--body-from-stdin`. Keep the body concise and
plain — other agents read it under context pressure.

## Tools

- `Read`, `Grep` — to inspect the hypothesis and its linked findings
- `Bash` — to invoke `python -m autolab.append_artifact` for emission

## Recommended model

`fable-5` — this is the creative, mechanism-level reasoning step; it is worth the
strongest model.

## Boundaries

- **Do not run any code or experiments.** This phase is pure reasoning; that is
  the whole point. The `design` and `run` phases come next.
- **Do not invoke other skills directly.** Return to the orchestrator after
  appending.
- **Do not contemplate scale before the toy rollout is done.** Scalability is the
  last step, never the first.
- **Prefer plain language.** State the mechanism so a smart non-specialist could
  follow it. If you can't say it plainly, you may not understand it yet.

## Stdout contract

End with one line:
```
phase=thought-experiment status=ok new_ids=TOY-001 verdict=<promising|inconclusive|refuted>
```

## Worked example

Hypothesis (HYP-007): "Injecting structured noise on a *schedule* borrowed from
simulated annealing lets a small transformer escape the loss plateau that fixed
weight-decay leaves it stuck on."

- **Mechanism (de-jargoned):** late-training plateaus are flat basins; a
  cooling-then-reheating noise schedule should knock the optimizer out of the
  basin early and let it settle once cooled.
- **Toy problem:** a 2-parameter loss surface with one wide shallow basin and one
  narrow deep basin (a hand-built double-well), optimized by SGD with vs. without
  the annealing noise schedule; watch which basin each run lands in over 50 runs.
  *Why this probes the claim:* it strips away the transformer entirely and tests
  only the escape-the-basin mechanism the hypothesis rests on.
- **Rollout:** under the hypothesis, the reheating phase should let annealed runs
  cross the ridge into the deep basin more often than the fixed-noise control;
  under the null, both land in whichever basin they started nearest. Divergence
  shows up as the fraction reaching the deep basin (expect ~70% vs. ~40%).
- **Failure modes:** if the noise scale is tuned per-run it confounds with a plain
  LR sweep; the double-well may be too easy to be informative; the effect could
  be specific to 2D and vanish in high dimensions.
- **Verdict:** `inconclusive` — the mechanism is coherent but whether it survives
  in a real loss landscape is exactly the open question; worth designing.
- **Scalability note:** first informative step is a small char-level transformer
  on a stack-manipulation task with a known plateau; the cheapest thing that
  would break it is the annealed and control runs converging to the same loss.

Append:
```
python -m autolab.append_artifact --type ThoughtExperiment \
  --parent HYP-007 \
  --author thought-experimenter \
  --summary "Annealing-schedule noise escapes loss basins — double-well toy probe is inconclusive, worth running" \
  --field hypothesis_id=HYP-007 \
  --field toy_problem="Hand-built 2D double-well; SGD with vs. without annealing noise; measure fraction reaching the deep basin over 50 runs" \
  --field predicted_outcome="annealed runs reach deep basin ~70% vs ~40% for fixed noise" \
  --field mechanism="reheating noise knocks the optimizer out of a shallow basin before it cools and settles" \
  --field verdict=inconclusive \
  --field scalability_note="next step: char-level transformer on a stack task with a known plateau; breaks if annealed and control losses converge" \
  --body-from-stdin
```
