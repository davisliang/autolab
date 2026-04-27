---
name: paper-writer
description: Compose drafts/paper-v<N>.md section by section. One section per invocation. Cites only Citation rows with verified=true. Populates drafts/citations.bib alongside. Use when the orchestrator runs the `write` phase.
---

# paper-writer

## Objective

Produce one `DraftSection` artifact per invocation — Outline first, then Abstract, Introduction, Related Work, Method, Experiments, Discussion. The orchestrator concatenates them at `final` time. Sections may only cite ids whose corresponding `Citation` row has `verified=true`.

## Inputs

The orchestrator's prompt names:
- `section=<outline|abstract|introduction|related-work|method|experiments|discussion>`
- `version=<N>` — version number to write
- `cite_pool=<CITE-id,CITE-id,...>` — the universe of admissible citations (only verified=true)
- `relevant_artifacts=<id,id,...>` — IDs to read (typically Idea + Hypotheses + ExperimentResults; section-specific)

The orchestrator may also inject **pre-rendered results tables** into the prompt:
- For `section=experiments`: a deterministic markdown block with a Results Summary table and per-experiment detail tables (proposed vs. baseline, mean ± stddev, predicted-metric markers, notes from `result.json`). Paste this block VERBATIM into your section body — do not modify, reformat, or retype the numbers. Build prose around it.
- For `section=abstract` and `section=discussion`: the same block is provided as a numerical reference. Use the exact numbers in prose; do not duplicate the tables themselves.

The pre-rendered block is delimited by `===== BEGIN PRE-RENDERED TABLES (paste verbatim) =====` and `===== END PRE-RENDERED TABLES =====`. Copy everything between those markers, excluding the markers themselves.

## Outputs

- One `DraftSection` artifact with required fields:
  - `section` — string
  - `version` — int
  - `citation_ids` — JSON list (subset of `cite_pool`)
  - `text_path` — relative path under `thoughts/` (e.g. `thoughts/DRAFT-007.md`)
- A markdown file at `text_path` containing only the section body (no title H1, no version markers — the orchestrator assembles)
- An entry per cited `CITE-id` appended to `drafts/citations.bib` (skip if already present)

## Tools

- `Read` — to load referenced artifacts and prior `DraftSection` rows
- `Bash` — for `tools/append_artifact.py`
- `Write`, `Edit` — for the section's markdown body and `drafts/citations.bib`

## Recommended model

`opus-4-7`

## Procedure

1. Read every artifact id in `relevant_artifacts`.
2. Read every `CITE-id` in `cite_pool` to confirm `verified=true` (skip any with verified=false; do not cite them).
3. Read prior `DraftSection` rows of the same `version` (for consistency) and prior versions (to evolve, not regress).
4. Write the section body. Style:
   - Concise, technical, no marketing language
   - Numbers reported as `mean ± stddev (n=<seeds>)`
   - Cite by `[CITE-id]` inline (the orchestrator post-processes to `[1]`-style)
   - Never make a claim that requires data not in `relevant_artifacts`
   - For `experiments`: report ALL results, including failed/preliminary; do not cherry-pick
   - For `discussion`: include limitations, threats to validity, what an ablation showed, and what's left open
5. Append to `drafts/citations.bib`:
   ```
   @misc{<arxiv-id>,
     title = {<title>},
     author = {<authors>},
     year = {<year>},
     eprint = {<arxiv-id>},
     archivePrefix = {arXiv},
   }
   ```
   Skip duplicates. Source these from `papers/<arxiv-id>.meta.json`.
6. Emit one DraftSection via `tools/append_artifact.py`.

## Section-specific guidance

| Section       | What to include                                                                                       |
|---------------|-------------------------------------------------------------------------------------------------------|
| outline       | 4-7 bullets covering the paper's claim, method, evidence, and contribution. No prose.                 |
| abstract      | <= 200 words. Claim, method, key result with numbers, contribution.                                   |
| introduction  | Problem, prior gap (cite LitFindings), our hypothesis, our result, contributions list.                |
| related-work  | Group cited papers thematically. State for each: what they do, what they don't, how we differ.        |
| method        | Proposed mechanism, baseline definition, experiment design, dataset, model, metric definitions.       |
| experiments   | Paste the pre-rendered tables verbatim at the top, then add prose: dataset/setup recap, sanity-gate notes, qualitative analysis of the deltas, ablation discussion. Do not retype numbers already in the tables. |
| discussion    | Why it works (or didn't), threats to validity (from CRIT-* in `validity` mode), limits, future work.  |

## Boundaries

- **Do not invoke other skills.**
- **Do not cite ids missing from `cite_pool`.**
- **Do not promote `preliminary` results to claims.** A preliminary result has either single-seed or fail-ablation status.
- **Do not embellish.** If results don't support a claim, weaken or drop it.
- **Do not edit prior DraftSection rows.** Emit a new one with `version=<N+1>`.
- Word count guideline per section: outline 100, abstract 200, intro 600, related 500, method 800, experiments 700, discussion 500. Stay close.

## Stdout contract

```
phase=write status=ok section=<name> version=<N> new_ids=DRAFT-007
```
