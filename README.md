# autolab

Autonomous research-loop. Point it at a one-line idea, walk away, come back to a paper draft with verified citations and reproducible experiments. All work is confined to this directory; the bot has its own `uv` venv and skill set.

```bash
./research --idea "investigate whether layer-wise learning rates help small MLPs on MNIST"
./research --resume                    # resume from latest checkpoint
./research --watchdog                  # spawn idle watchdog for hands-off operation
./research --resume-from-bank          # pick up an idea from ideas/parking_lot.md
./research --benchmark mnist           # bias the experiment-designer toward a tracked benchmark suite
```

## Architecture

The bot is a `claude` CLI loop. Each phase is a fresh headless `claude -p` subprocess; subagents are skills under `skills/<name>/SKILL.md` that auto-load from cwd. Subagents communicate through a typed shared thread on disk — never via chat — referencing each other by stable artifact ID.

```
seed → expand → survey → gap-fill → screen → design → run → critique → write → final
```

Each phase ends with a checkpoint at `thread/checkpoints/<phase>.json`. The loop is resumable.

### Subagents

| Skill                | Role                                                                 | Model     |
| -------------------- | -------------------------------------------------------------------- | --------- |
| `idea-expander`      | Seed Idea -> Hypotheses (incl. cross-domain transplant + gap-fill)   | Sonnet    |
| `literature-scout`   | Pull related work via HF papers + arXiv + Semantic Scholar           | Sonnet    |
| `novelty-checker`    | Fuzzy-title verify each Hypothesis vs LitFindings                    | Haiku     |
| `experiment-designer`| Best-first search; emit ExperimentPlan (multi-seed + baseline)       | Opus      |
| `experiment-runner`  | Sanity-gate + run + log; auto-ablate on pass; failure-analysis retry | Sonnet    |
| `critic`             | Validity / boredom / failure-analysis modes                          | Opus      |
| `paper-writer`       | Section-by-section, only verified citations                          | Opus      |

Plus the bundled `huggingface-papers` skill (used by literature-scout, novelty-checker).

### Layout

```
autolab/
├── program.md            # protocol the orchestrator reads each tick
├── research              # entry point
├── tools/                # orchestrator, watchdog, artifact tools
├── skills/               # one dir per subagent + huggingface-papers
├── thread/               # log.jsonl + INDEX.md + checkpoints/
├── papers/               # fetched arxiv markdown + INDEX.md
├── thoughts/             # one MD per artifact id (long-form companion)
├── experiments/          # one subdir per ExperimentPlan id
├── drafts/               # paper-v<N>.md + citations.bib
├── ideas/                # parking_lot.md for un-pursued ideas
└── logs/                 # orchestrator.log + cost_ledger.tsv + watchdog.log
```

## Quality gates (default-on)

- **Pre-registered predictions** — every Hypothesis commits to a numeric threshold before it gets resources.
- **Cross-domain ideation** — idea-expander must propose at least one hypothesis importing a technique from a distant subfield.
- **Negative-space ideation** — second idea-expander pass identifies the question conspicuously absent from the LitFinding set.
- **Boredom-critic** — critic argues against each Hypothesis as "trivial / known / dead end" before it advances.
- **Multi-seed + matched-budget baseline** — every ExperimentPlan ships ≥3 seeds and a same-compute baseline; runner rejects plans missing either.
- **Sanity gate** — every model must overfit a tiny subset (32 examples) before the main run, or the experiment aborts.
- **Auto-ablation** — every passing experiment triggers exactly one ablation isolating the proposed mechanism.
- **Failure analysis** — between failed retries, the critic explains why before the runner patches.
- **Reproducibility envelope** — `experiments/<id>/repro.sh` captures seeds, code hash, env hash, command line.
- **Cost ledger** — `logs/cost_ledger.tsv` rows per skill invocation: phase | skill | model | tokens | usd.
- **Persistent idea bank** — un-pursued hypotheses go to `ideas/parking_lot.md` and survive across runs.

## Setup

```bash
cd /Users/davis/Documents/code/autolab
uv sync
# Optional: cp .env.example .env  (only needed for API-key billing or HF write ops)
```

Authentication: Claude Code subscription OAuth works out of the box. No `ANTHROPIC_API_KEY` required.

## Verification (smoke)

```bash
./research --idea "investigate whether layer-wise learning rates help small MLPs on MNIST"
```

Expect after ~10–20 min:
- `thread/log.jsonl` populated across all artifact types
- `papers/` has ≥5 fetched markdown copies
- `experiments/EXP-001/runs/` has logs and `result.json` with mean ± stddev
- `experiments/EXP-001/repro.sh` exists and is executable
- `drafts/paper-vFINAL.md` exists with Abstract / Intro / Related / Method / Experiments / Discussion
- `drafts/citations.bib` contains only `verified=true` citations
- `logs/cost_ledger.tsv` shows per-phase spend

## Design notes

- **Process boundary = context boundary.** Each phase is a fresh `claude -p` call. No transcript carryover across phases. Compaction is a fallback, not a strategy.
- **Read-by-handle.** Agents read `thread/INDEX.md` first and only `Read` the specific `thoughts/<id>.md` files they need.
- **Append-only.** Agents never edit prior thread/thoughts entries; corrections go in new Critique artifacts.

## Inspirations

`autogolf-mlx` (loop pattern, program.md, idle watchdog), Sakana AI Scientist v2 (BFTS), Co-STORM (typed shared artifact > chat log), Anthropic multi-agent research system (orchestrator-worker, prescriptive delegation), Agent Laboratory (phase checkpoints), PaperOrchestra (two-phase citation grounding).
