---
name: novelty-checker
description: Verify each Hypothesis is non-duplicative against the LitFinding set via fuzzy title-match and claim-overlap heuristics. Emits Critique on collision and Citation rows for each verified neighbor. Use when the orchestrator runs the `screen` phase (novelty pass).
---

# novelty-checker

## Objective

For each surviving `Hypothesis`, decide whether the literature already answers it. The check is conservative: prefer false positives (over-collide → park to ideas) to false negatives (let a duplicate idea waste experiments).

## Inputs

- `thread/INDEX.md` for the full LitFinding set
- Each `Hypothesis` body via `thoughts/HYP-*.md`

## Outputs

For each `Hypothesis`:
- `Citation` rows — one per LitFinding that materially overlaps, with `verified` (bool), `verifier_score` (0-1), `verifier_method` ("title-match" | "claim-overlap" | "manual")
- `Critique` row with `mode="validity"` and `severity="high"` if collision is severe (verifier_score >= 0.85 on title-match OR exact claim restatement)

The orchestrator uses high-severity Critiques to park the hypothesis.

## Tools

- `python -m autolab.verify_citation --claim "<text>" --candidate-arxiv-ids <id,id,...>` — runs fuzzy title-match via rapidfuzz + Semantic Scholar lookup; prints score per candidate
- `Read` — to inspect Hypothesis + LitFinding bodies

## Recommended model

`fable-5`

## Procedure

1. Read every `thoughts/HYP-*.md` listed by the orchestrator.
2. For each Hypothesis, build a candidate LIT subset: all LitFindings whose `parent_ids` include this hypothesis OR whose `key_claims` mention any of the hypothesis's claim nouns.
3. For each (Hypothesis, LitFinding) pair:
   a. Run `python -m autolab.verify_citation --claim "<hyp.claim>" --candidate-arxiv-id <lit.arxiv_id>`
   b. Parse the score
   c. Emit a `Citation` row with `verified=true` if score >= 0.5, else `verified=false`
4. If max(verifier_score) over all candidate LITs is >= 0.85: emit a high-severity `Critique` (mode=validity) flagging duplication and listing the overlapping LIT id(s).
5. Otherwise: leave the Hypothesis alone (orchestrator will advance it to `design`).

## Boundaries

- **Do not invoke other skills.**
- **Do not fabricate Citation rows for papers not in the LitFinding set.** If the hypothesis names an obvious prior work that scout missed, emit a `Critique` recommending another scout pass instead of inventing a Citation.
- **Do not edit prior Citation rows.** New evidence -> new Citation row, possibly superseding (link via parent_ids).
- Verifier scores in `Citation` are JSON numbers, not strings.

## Stdout contract

```
phase=screen-novelty status=ok new_ids=CITE-014,CITE-015,CRIT-007 parked_hypotheses=HYP-002
```

## Worked example

For HYP-003 vs. LIT-008 (a paper on layer-wise adaptive rates):
```
python -m autolab.verify_citation \
  --claim "Trust-region-style per-layer LR scaling outperforms uniform LR on MNIST MLPs" \
  --candidate-arxiv-id 2412.00123
```
If score = 0.92 (very close) -> emit CITE row with verified=true AND a high-severity Critique (collision). The orchestrator parks HYP-003.

If score = 0.42 -> emit CITE row with verified=false (these are the "this isn't the same thing" results that nonetheless context the writer).
