---
name: paper-polisher
description: Polish an already-assembled drafts/paper-vFINAL.md by editing it in place. Fill any '_(missing)_' or sparse sections, tighten weak prose, and enforce cross-section consistency (intro contributions ↔ experiments table). Does NOT emit DraftSection artifacts; the polished file IS the deliverable. Invoked once at the end of `phase_final` after the section-by-section assembly.
---

# paper-polisher

## Objective

Take the assembled `drafts/paper-vFINAL.md` and produce a more **complete** and more **readable** version, in place. This is a single-call skill — no DraftSection artifacts are emitted; the file on disk is the deliverable.

This step exists because the section-by-section `phase_write` calls sometimes leave gaps: a section's DraftSection may be missing entirely (rendered as `_(missing)_` by `phase_final`), or its body may be sparse, or two sections may contradict each other on numbers or framing. The polisher catches those problems after the full paper is in front of it, where they're visible.

## Inputs

The orchestrator's prompt names:
- `paper_path` — path to the assembled paper (relative to repo root); edit this file in place
- `backup_path` — pre-polish snapshot; do **not** edit this file (kept for diffing)
- `cite_pool=<CITE-id,CITE-id,...>` — verified citations available for use
- `relevant_artifacts=<id,id,...>` — ids you may need to read for grounding (Idea + Hypotheses + ExperimentResults + validity Critiques)

A pre-rendered results-tables block is also injected as the canonical numerical anchor. Numerical claims in prose must agree with these tables.

## Outputs

- The polished `paper_path` (overwriting the input)
- No artifact emissions, no new files, no edits anywhere else
- A one-line stdout summary at the end (see contract below)

## Tools

- `Read` — load the paper, artifacts, `drafts/citations.bib`, and the results tables
- `Edit` — preferred for surgical changes
- `Write` — for whole-section rewrites of a `_(missing)_` placeholder
- No `Bash`, no other skills — this is a focused, self-contained pass

## Recommended model

`fable-5`

## Procedure

1. Read `paper_path`. Note which sections are present and their lengths.
2. Identify gaps:
   - Sections whose body is `_(missing)_` or empty.
   - Sections shorter than ~3 sentences (likely incomplete).
   - Sections containing placeholder language ("TODO", "(missing)", "(to be filled)").
3. Read the relevant artifacts in `relevant_artifacts`. Use the `Idea`, `Hypothesis`, `ExperimentPlan`, `ExperimentResult`, and validity-mode `Critique` rows as the source of truth for any factual or numerical claim.
4. Read `drafts/citations.bib` to confirm which citation keys are usable. Cite only ids in `cite_pool`.
5. Use the NeurIPS structural standard from `skills/paper-writer/SKILL.md` as your rubric for what each section should contain. Section-specific guidance there applies here verbatim.
6. For each gap, fill the section with a complete body matching the surrounding register and length. Ground every claim in the artifacts and tables; do not fabricate numbers, results, or experiments.
7. Do a clarity and narrative pass on the rest of the paper:
   - **Check narrative flow:** Does each section open by connecting to the previous one? Does the paper read as a coherent story (question → approach → evidence → lesson) rather than a stack of disconnected technical cards?
   - **Check pedagogical clarity:** Would a smart graduate student follow this without re-reading? Where intuition is missing before formalism, add a motivating sentence. Where results are reported without interpretation, add a "this tells us..." sentence.
   - **Tighten weak prose:** Convoluted sentences, marketing language ("novel", "state-of-the-art", "significant"), and passive-voice hedging. Replace with direct, concrete claims.
   - Remove duplicated phrasing across sections.
   - Verify that the introduction's contributions bullet list and the experiments headline table tell the *same story* 1-for-1.
   - Spot-check that every numerical claim in prose matches the pre-rendered results tables.
   - For negative-results work, lead with the falsified prediction; do not soften "fail" into "promising trend" if a pre-registered threshold was missed.
   - **Check for "wall of details" anti-pattern:** If any section dumps specifications, numbers, or citations without explaining *why* the reader needs them, restructure to lead with motivation.
8. **Scrub internal identifiers.** Search the paper for any `HYP-`, `EXP-`, `CRIT-`, `LIT-`, `RES-`, `REV-`, `DRAFT-`, `CITE-` prefixed IDs (pattern: uppercase letters followed by a dash and digits). Replace each with a descriptive phrase. Also replace pipeline jargon ("decisively refuted", "downgraded to preliminary", "parked", "wildness bar", "retreat cycle") with standard academic language.
9. Edit the file in place via `Edit` (preferred; sends only the diff) or `Write` (for whole-section rewrites). Preserve the title line and every section heading exactly — do not renumber, add, or remove sections.
10. Print the stdout contract.

## Style

- Concise, technical, no marketing language.
- Numbers reported as `mean ± stddev (n=<seeds>)`.
- Use only verified citations from `cite_pool`. Inline citations as `[CITE-id]`.
- Match the prose register and length of the surrounding sections; do not balloon a 200-word abstract into 500.
- **Conference-ready language:** This paper is being submitted to a peer-reviewed conference. Scrub ALL internal artifact IDs (`HYP-*`, `EXP-*`, `CRIT-*`, `LIT-*`, `RES-*`, `REV-*`, `DRAFT-*`, or any `PREFIX-NNN` pattern) from the prose — replace with descriptive references. Also remove pipeline jargon ("decisively refuted", "downgraded to preliminary status", "parked", "wildness bar", "retreat cycle", "loopback"). Use standard academic language throughout.

## Boundaries

- **Do not invoke other skills.**
- **Do not add or remove section headings.** The structure is fixed by `phase_final`'s assembly order.
- **Do not introduce new citations** outside `cite_pool`.
- **Do not edit the numbers in the pre-rendered results tables** or in any results-bearing prose. Use the canonical tables as the single source of truth.
- **Do not fabricate experiments, datasets, or results** that aren't in the artifacts.
- **Do not write outside `paper_path`.** The orchestrator already created `backup_path`; you must not touch it, and you must not create new files.
- **Do not edit prior `DraftSection` rows or `thoughts/<id>.md`.** This pass operates only on the assembled paper.
- **Do not skip pre-commit hooks** (`--no-verify`) or other safety nets. You are not running git commands.

## Stdout contract

```
phase=polish status=ok sections_filled=<N> sections_revised=<M>
```

Where:
- `N` = number of sections that were missing/empty before polish and now have a body
- `M` = number of sections whose body was substantively rewritten (more than typo fixes)
