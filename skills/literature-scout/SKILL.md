---
name: literature-scout
description: Pull related work for a Hypothesis or Idea. Fetches paper markdown, extracts key claims, emits LitFinding rows. Uses the Hugging Face Papers API, arXiv API, and Semantic Scholar. Use when the orchestrator runs the `survey` phase.
---

# literature-scout

## Objective

Given a target `Hypothesis` (or `Idea`), gather 3-7 papers that are most relevant — for, against, or directly adjacent. Fetch their markdown bodies into `papers/`, extract structured `LitFinding` rows into the thread, and update `papers/INDEX.md`.

## Inputs

- The target id from the orchestrator prompt (e.g. `HYP-003`)
- Read `thoughts/<id>.md` for that target
- Optionally read `thread/INDEX.md` to avoid duplicating LIT-rows you already have

## Outputs

`LitFinding` artifacts via `python -m autolab.append_artifact`. Required fields:
- `arxiv_id` — string (e.g. `2412.00123`)
- `title` — string
- `relevance` — float in [0, 1]
- `key_claims` — JSON list of 1-3 short strings (one claim per element)
- `paper_path` — relative path `papers/<arxiv-id>.md`

Side effects:
- `papers/<arxiv-id>.md` and `papers/<arxiv-id>.meta.json` populated via `python -m autolab.fetch_paper`
- `papers/INDEX.md` refreshed via `python -m autolab.refresh_indexes --papers`

## Tools

- The `huggingface-papers` skill (loaded from `skills/huggingface-papers/SKILL.md`) — use its API recipes
- `python -m autolab.fetch_paper <arxiv-id>` — caches paper markdown + metadata
- `WebFetch` — for arXiv search and Semantic Scholar fallback
- `Read`, `Grep` — to inspect fetched paper bodies

## Recommended model

`fable-5`

## Procedure

1. Read the target `thoughts/<id>.md`. Identify 3-5 search queries (claim verbs + nouns).
2. Search via the HF Papers API first:
   ```
   curl "https://huggingface.co/api/papers/search?q=<query>&limit=10"
   ```
   Then arXiv (`http://export.arxiv.org/api/query?search_query=...`) for breadth.
3. For each candidate paper:
   a. Run `python -m autolab.fetch_paper <arxiv-id>` to cache markdown + metadata
   b. Read the abstract + intro from `papers/<arxiv-id>.md`
   c. Decide relevance (0-1). Keep ≥0.4 only.
4. For each kept paper: extract 1-3 `key_claims` as short strings (e.g. "Per-layer LR helps for ResNets on ImageNet (>0.5pp top-1)").
5. Emit one `LitFinding` per paper via `python -m autolab.append_artifact`.
6. After all emissions: run `python -m autolab.refresh_indexes --papers`.

## Boundaries

- **Do not invoke other skills.** The orchestrator drives all cross-skill calls.
- **Do not fabricate arxiv IDs.** If a search returns nothing, report fewer findings; do not guess.
- **Do not extract more than 3 claims per paper.** The thread is context-bounded.
- **Do not edit existing LitFinding rows.** Add a new Critique if a finding turns out wrong.
- Stay within the network allowlist: arxiv.org, huggingface.co, api.semanticscholar.org.

## Stdout contract

```
phase=survey status=ok target=<HYP-id> new_ids=LIT-007,LIT-008,LIT-009
```

## Worked example

Target: HYP-003 ("Trust-region-style per-layer LR scaling outperforms uniform LR on MNIST MLPs").

Searches:
- "per-layer learning rate scaling neural network"
- "adaptive layer-wise optimizer"
- "trust region stochastic optimization"

For each hit, fetch + read abstract, score relevance, emit LIT row. Record at least one for-paper, one against-paper if such exists.
