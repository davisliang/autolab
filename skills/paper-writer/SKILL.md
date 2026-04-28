---
name: paper-writer
description: Compose drafts/paper-v<N>.md section by section to a NeurIPS-quality structure. One section per invocation. Cites only Citation rows with verified=true. Populates drafts/citations.bib alongside. Use when the orchestrator runs the `write` phase.
---

# paper-writer

## Objective

Produce one `DraftSection` artifact per invocation, contributing to a NeurIPS-style paper. The orchestrator concatenates the sections at `final` time. Sections may only cite ids whose corresponding `Citation` row has `verified=true`.

## NeurIPS structural standard (authoritative reference)

This is the structure the assembled paper must satisfy. Each section below is an independently invoked DraftSection; honor this standard regardless of which section you are writing.

**Title and Abstract.** Title is 10–15 words, either naming the method (`MethodName: What It Does`) or leading with the result. Abstract is 150–250 words and follows: problem → gap in prior work → approach → 2–3 headline results with concrete numbers → takeaway. Commit to specific claims (e.g. "3.2× throughput at matched perplexity on 7B models"), not vague gestures. For negative-results papers, lead with the refutation and quantify the falsified prediction.

**Introduction (~1 page).** Hook establishing why the problem matters; brief survey of what's been tried and what's missing; one paragraph sketching the approach; an explicit contributions bullet list of *falsifiable claims* (not activities); and a Figure 1 teaser — either a method diagram or a money-plot of the headline result.

**Related Work.** Either §2 (contextual framing before the method) or near the end (positioning after the contribution is clear). Organize by themes; end each paragraph by distinguishing the contribution from that cluster. Lists of citations without positioning are a red flag.

**Background / Preliminaries.** Notation, problem setup, formal definitions, and prior results the paper builds on. The bar: a reader fluent in the area should be able to read the method without bouncing to external papers, but textbook material is not re-derived. Sometimes folded into Method if notation is standard.

**Data and Models (~1–1.5 pages).** *Data:* named sources with sizes, licenses, and collection dates; mixture weights for pretraining-scale work; preprocessing pipeline (tokenization, dedup, quality and safety filtering, in order); train/val/test splits and construction; explicit decontamination against eval sets; summary statistics (token counts, length distribution, domain or label balance); pointer to a datasheet in the appendix if the data is novel. Avoid "large web corpus" and "standard preprocessing." *Models:* full architecture spec ($L$, $d_\text{model}$, $d_\text{ff}$, heads $h$, head dim $d_h$, KV heads, vocab, max sequence length, position encoding, normalization, activation, any non-standard pieces); parameter count table with breakdown (active vs total for MoE); tokenizer details; brief training recipe (optimizer, schedule, batch size, total tokens, precision) with full details in appendix; compute footprint (hardware, GPU-hours, FLOPs); checkpoint conventions and release plans. Justify non-default choices. *Consistency check:* every component named here must reappear in the method if it's load-bearing; every dataset must reappear in training or evaluation. Orphans signal cut scope.

**Method (~2–3 pages).** Formal problem statement with locked notation; the algorithm or architecture with pseudocode and/or a diagram; theoretical analysis when applicable (assumptions stated, theorem statements and proof sketches in main text, full proofs in appendix); design choices with rationale — why this loss, this parameterization, this routing scheme; complexity analysis (compute, memory, communication) where relevant. Common failure: presenting the method as a sequence of tricks without articulating which choices are load-bearing.

**Experiments (~2–3 pages).** *Setup:* datasets, model sizes, baselines, metrics, compute, key hyperparameters — enough for a competent reader to attempt reproduction. *Main results:* one headline table or plot delivering the contribution claim; baselines must be strong and current. *Ablations:* per-component contribution. **N claimed ideas → N ablations.** *Analysis:* scaling behavior, qualitative inspection, probes, failure cases. Where reviewers decide whether you understand your own method. *Robustness:* seed variance, hyperparameter sensitivity, OOD evaluation. **Error bars or seed counts on every number. Single-seed RL results get hammered.**

**Discussion / Limitations.** NeurIPS requires this. Name *specific* threats to validity (distributions not tested, scales not reached, baselines not run, assumptions that may not hold) rather than performing humility. Specific beats generic.

**Conclusion.** A paragraph. Restate the contribution and point at future work. **No new claims.**

**Broader Impact Statement.** Required. Be concrete about dual-use, misuse vectors, and downstream effects specific to the contribution, not boilerplate. For pure methods papers, you may argue impact is mediated by applications — but argue it.

**Reproducibility Statement.** Pointer to where code, data, hyperparameters, and compute details live (appendix and code release).

**References.** No page limit. Should be current — papers from the last 6–12 months in fast-moving areas.

**Appendix.** Doesn't count toward the 9-page main limit. Contains: full proofs and derivations; per-experiment hyperparameter tables; extended ablations and seeds; additional baselines; compute breakdown; datasheets and model cards; failure case analyses and qualitative samples; implementation details (kernels, distributed setup, precision). Reviewers read this — treat it as part of the paper.

**Top-level consistency check.** The contributions bullets in the introduction and the headline table or figure in Experiments must tell the same story. A reviewer who reads only those two things should walk away with the right takeaway; the rest of the paper is doing its supporting job.

## Inputs

The orchestrator's prompt names:
- `section=<outline|abstract|introduction|related-work|background|data-models|method|experiments|discussion|conclusion|broader-impact|reproducibility>`
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
3. Read prior `DraftSection` rows of the same `version` (for consistency) and prior versions (to evolve, not regress). **In particular, before writing any section other than `outline` or `introduction`, re-read the latest `introduction` DraftSection and ensure your section's claims and language are consistent with the contributions list.**
4. Write the section body. Style:
   - Concise, technical, no marketing language
   - Numbers reported as `mean ± stddev (n=<seeds>)`
   - Cite by `[CITE-id]` inline (the orchestrator post-processes to `[1]`-style)
   - Never make a claim that requires data not in `relevant_artifacts`
   - For `experiments`: report ALL results, including failed/preliminary; do not cherry-pick
   - For `discussion`: include limitations, threats to validity, what an ablation showed, and what's left open
   - For negative results: lead with the falsified prediction and quantify it; do not soften "fail" into "promising trend" if the pre-registered threshold was missed
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

## Section-specific guidance (NeurIPS quality bar)

| Section          | What to include                                                                                                                                                                                                          |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| outline          | 4–7 bullets covering claim, method, evidence, contribution. No prose. Confirms the contributions list that will appear in the introduction.                                                                              |
| abstract         | 150–250 words. Problem → gap → approach → 2–3 headline numbers → takeaway. Commit to specific claims with numbers; reuse numbers verbatim from the pre-rendered tables.                                                  |
| introduction     | ~1 page. Hook → brief survey of prior attempts and their gap → one-paragraph approach sketch → explicit contributions bullet list of *falsifiable claims* (each bullet is something a reviewer could disprove with data). Mention a Figure 1 teaser even if the figure is not yet rendered. |
| related-work     | Group cited papers thematically. State for each cluster: what they do, what they don't, how we differ. End each paragraph with an *"Our work differs..."* positioning sentence. No bare citation lists.                  |
| background       | Notation, problem setup, formal definitions, prior results we build on. Self-contained for a reader fluent in the area. Do not re-derive textbook material. May be folded into method if notation is standard — if so, emit a placeholder noting the merge. |
| data-models      | Full data spec (sources, sizes, licenses, dates, mixture weights, preprocessing pipeline in order, splits, decontamination, summary statistics) and full model spec ($L$, $d_\text{model}$, $d_\text{ff}$, $h$, $d_h$, KV heads, vocab, max seq len, position encoding, norm, activation, parameter count table, tokenizer, training recipe, compute footprint, checkpoint plans). Justify non-default choices. Run a consistency check: every component reappears in method; every dataset reappears in training/eval. |
| method           | Formal problem statement with locked notation, algorithm/architecture with pseudocode or diagram, theoretical analysis where applicable (assumptions, theorem statements, proof sketch; full proofs to appendix), design choices with rationale, complexity analysis. Articulate which choices are load-bearing.                                                            |
| experiments      | Paste the pre-rendered tables verbatim at the top, then add prose: setup recap (datasets, model sizes, baselines, metrics, compute, key hyperparameters), main results discussion, **ablations matching the contributions list 1-for-1** (N claimed ideas → N ablations), analysis (scaling, qualitative, probes, failure cases), robustness (seeds, hyperparameter sensitivity, OOD). **Error bars or seed counts on every number.** Do not retype numbers already in the tables. |
| discussion       | Why it works (or didn't), *specific* threats to validity from CRIT-* artifacts (distributions not tested, scales not reached, baselines not run, assumptions that may not hold), limits, future work. Specific beats generic. For negative results, name what would constitute positive evidence (scale, task, regime, effect-size recalibration). |
| conclusion       | One paragraph. Restate the contribution and point at future work. **No new claims.** ≤ 150 words.                                                                                                                        |
| broader-impact   | Concrete on dual-use, misuse vectors, and downstream effects specific to the contribution, not boilerplate. For pure methods papers, argue the impact-mediation chain rather than asserting "limited risk." Address both the positive case (negative results redirect effort, etc.) and the residual concerns. |
| reproducibility  | Concrete pointers: code path, data path, per-experiment hyperparameter tables, pretrain caches, run logs, statistical-analysis scripts, pre-registration commit hash. Note non-determinism caveats explicitly (e.g., MLX on Apple Silicon).                              |

## Top-level consistency rule

The contributions bullets in `introduction` and the headline table in `experiments` must tell the same story. A reviewer who reads only those two artifacts must walk away with the right takeaway. Before emitting your section, sanity-check that your section's narrative is compatible with both.

## Boundaries

- **Do not invoke other skills.**
- **Do not cite ids missing from `cite_pool`.**
- **Do not promote `preliminary` results to claims.** A preliminary result has either single-seed or fail-ablation status.
- **Do not embellish.** If results don't support a claim, weaken or drop it.
- **Do not edit prior DraftSection rows.** Emit a new one with `version=<N+1>`.
- **Do not retype numbers from the pre-rendered tables in prose.** Reference them and add interpretation.
- Word count guideline per section: outline 100, abstract 200, intro 700, related 600, background 400, data-models 800, method 900, experiments 900, discussion 600, conclusion 150, broader-impact 250, reproducibility 250. Stay close.

## Stdout contract

```
phase=write status=ok section=<name> version=<N> new_ids=DRAFT-007
```
