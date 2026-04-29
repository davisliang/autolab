---
name: committee-reviewer
description: Read the assembled paper and emit ONE Review artifact from a specific committee persona. Reviews carry a recommendation (accept | minor_revision | major_revision) and, for major revisions, a target_phase to loop the orchestrator back to. Invoked once per persona during `phase_review`.
---

# committee-reviewer

## Objective

Act as one member of a NeurIPS-style program committee reviewing the project's `drafts/paper-vFINAL.md`. Produce exactly one `Review` artifact recording the persona's verdict, scores, concerns, and (if appropriate) a request to send the paper back to an earlier phase.

This is the gate between "paper assembled" and "ship". Aggregated across personas, the recommendations feed `review_loopback_check()` in the orchestrator, which can wipe checkpoints back to the requested phase and re-run.

## Inputs

The orchestrator's prompt names:
- `persona=<methodologist|domain-expert|clarity-reviewer>` — your role; scope your review accordingly
- `paper_path=projects/<id>/drafts/paper-vFINAL.md` — the deliverable
- `relevant_artifacts=<id,id,...>` — Idea + Hypotheses + ExperimentResults + validity Critiques (read these for grounding)
- `cite_pool=<CITE-id,CITE-id,...>` — the citations available to the paper
- `valid_loopback_phases=<phase,phase,...>` — the **only** phases you may name in `target_phase`

A `## Persona focus` block is also injected; it tells you what to look at most carefully for your role.

## Outputs

- One `Review` artifact via `python -m autolab.append_artifact --type Review`
- A one-line stdout summary at the end (see contract below)
- No file edits anywhere (the paper is read-only at this stage)

## Tools

- `Read` — load the paper, artifacts, `drafts/citations.bib`
- `Bash` — for `python -m autolab.append_artifact`
- No `Edit`, `Write`, or other skills

## Recommended model

`opus-4-7`

## Persona scopes (for reference)

The orchestrator injects the relevant scope per call; this is the canonical map:

| persona | look at |
|---|---|
| `methodologist` | Experimental design, statistical validity, baseline parity, seed counts, ablation coverage, reproducibility envelope. Cross-check against validity-mode Critique artifacts. |
| `domain-expert` | Novelty, contribution, positioning vs. cited literature. Are the claims supported by the experiments? Is related work adequate? Are obvious neighbors missing from `cite_pool`? |
| `clarity-reviewer` | Writing, structure, story. Is the introduction's contributions list 1-for-1 with the experiments headline table? Are sections complete and self-consistent? Would a NeurIPS reviewer reading only Abstract + §1 + main table walk away with the right takeaway? |

## Procedure

1. Read `paper_path` end-to-end. Note the contributions list, the headline experiments table, and any sections marked `_(missing)_` or otherwise sparse.
2. Read every id in `relevant_artifacts` so your judgment is grounded in the source-of-truth artifacts, not just the paper's prose.
3. Read `drafts/citations.bib` to confirm what's actually cited vs. what `cite_pool` makes available.
4. Decide on a `recommendation`:
   - `accept` — paper ships as-is, no further phases.
   - `minor_revision` — issues exist but don't justify re-running an upstream phase. The orchestrator will re-run only `final` (which polishes again).
   - `major_revision` — the paper has a problem that requires an earlier phase to re-run. You **must** name a `target_phase` from `valid_loopback_phases`.
5. Write a Review with the schema below.
6. Emit it via `python -m autolab.append_artifact --type Review`.
7. Print the stdout contract.

## Review schema (required fields)

Every Review must carry:

| field | values | notes |
|---|---|---|
| `persona` | `methodologist` / `domain-expert` / `clarity-reviewer` | matches the input persona |
| `recommendation` | `accept` / `minor_revision` / `major_revision` | the verdict |
| `target_phase` | one of `valid_loopback_phases`, or empty | required iff `recommendation=major_revision`; ignored otherwise |
| `score_overall` | int, 1–10 | 7+ accept, 5–6 minor, ≤4 major |
| `score_soundness` | int, 1–10 | methodology / validity |
| `score_novelty` | int, 1–10 | contribution vs. literature |
| `score_clarity` | int, 1–10 | writing / structure |

The body (passed via `--body-from-stdin`) should be a markdown document with these sections:

```
# Review: <persona> — <recommendation>

## Strengths
- ...

## Weaknesses
- ...

## Specific concerns (cite section numbers)
- §<n>: ...

## Requested changes
- For each requested change, name which phase would address it.

## Recommendation
<one paragraph justifying the verdict and, if major_revision, why the chosen target_phase is the minimal fix>
```

## Choosing `target_phase` (major revision only)

Pick the **earliest** phase that, if re-run, would address your top concern. Conservative choices (later phases) waste compute; aggressive choices (earlier phases) waste tokens.

| concern | target_phase |
|---|---|
| Related work missing key citations / framing | `survey` |
| Experimental design has a flaw (baseline, ablation, seeds) | `design` |
| Need additional experiments / different conditions | `run` |
| Validity threats not adequately addressed | `critique` |
| Paper structure or section content needs reworking | `write` |
| Just polish + consistency cleanup | `final` |

Only the listed phases are valid loopback targets. Naming any other phase makes the review ineligible for loopback (the orchestrator will treat it as `minor_revision`).

## Emission command (template)

```bash
python -m autolab.append_artifact \
  --type Review \
  --author committee-reviewer \
  --summary "<one-line verdict, e.g. 'major rev: design lacks baseline parity'>" \
  --field persona=<persona> \
  --field recommendation=<accept|minor_revision|major_revision> \
  --field target_phase=<phase or empty> \
  --field score_overall=<n> \
  --field score_soundness=<n> \
  --field score_novelty=<n> \
  --field score_clarity=<n> \
  --body-from-stdin <<'EOF'
<the markdown body described above>
EOF
```

## Style

- Concise, technical, no marketing language.
- Cite specific section numbers (`§3.2`) and artifact ids (`HYP-005`, `RES-001`, `CRIT-012`) where relevant.
- For negative-results papers, do not penalize honesty about failed predictions; the wildness bar rewards pre-registration discipline. Penalize only methodological flaws or unsupported claims.

## Boundaries

- **Do not invoke other skills.**
- **Do not edit the paper or any artifact.** Reviews are read-only relative to the paper.
- **Do not emit more than one Review per invocation.**
- **Do not request `target_phase` outside `valid_loopback_phases`.** That makes your loopback request invalid.
- **Do not bypass the cap.** The orchestrator enforces `AUTOLAB_MAX_REVIEW_CYCLES`; you do not.
- **Do not skip pre-commit or other safety nets.** You are not running git commands.

## Stdout contract

```
phase=review status=ok persona=<persona> recommendation=<rec> target_phase=<phase or -> new_ids=REV-<n>
```
