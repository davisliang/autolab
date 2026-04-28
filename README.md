# autolab

Autonomous research-loop. Point it at a one-line idea, walk away, come back to a paper draft (Markdown + optional PDF) with verified citations, deterministic results tables, and reproducible experiments. Each run lives in its own project directory; subagents communicate through a typed shared thread on disk — never via chat — referencing each other by stable artifact ID.

## Quick start

```bash
# new project — argv quoting
./start --idea "investigate whether layer-wise learning rates help small MLPs on MNIST"

# new project — long ideas without shell-quoting headaches
./start --idea-file my-idea.txt
./start --idea-stdin <<'EOF'
... multi-line idea, apostrophes/quotes fine ...
EOF

# pick up where it left off
./resume                                  # interactive picker
./resume --project <id>                   # by id
./resume --project <id> --hypothesis "user-supplied claim"
./resume --project <id> --resume-from-bank   # pop next parked HYP
./resume --list                           # print the project table

# live progress dashboard (separate terminal)
uv run python tools/dashboard.py          # http://127.0.0.1:8765
```

To stop a running orchestrator: Ctrl+C its terminal, or `touch STOP` at the repo root, or `pkill -f run_orchestrator.py`.

## Architecture

The bot is a `claude` CLI loop. Each phase is a fresh headless `claude -p` subprocess; subagents are skills under `skills/<name>/SKILL.md` that auto-load from cwd. Every run creates one project directory under `projects/<slug>-<YYYYMMDD>[-N]/` containing its own thread, papers, thoughts, experiments, drafts, and logs.

### Phase pipeline

```
seed → expand → survey → gap-fill → screen → design → run → critique → write → final
                              ↑                                  │
                              │  experiment retreat (no pass)    │
                              └──────────────────────────────────┘
                  ↑              │
                  │ idea retreat │
                  │ (too boring) │
                  └──────────────┘
```

| Phase | Skill (mode) | Model | What it does |
|-------|--------------|-------|--------------|
| `seed` | — (orchestrator) | — | Emits one `Idea` artifact from your `--idea` |
| `expand` | `idea-expander` (expand) | Sonnet | 3-5 `Hypothesis` artifacts; ≥1 must be a W1 cross-domain transplant from a non-ML field |
| `survey` | `literature-scout` | Sonnet | Per-hypothesis paper search; emits `LitFinding` rows |
| `gap-fill` | `idea-expander` (gap-fill) | Sonnet | 1-2 more `Hypothesis` rows targeting what the lit set conspicuously misses |
| `screen` | `critic` (boredom) ‖ `novelty-checker` | Haiku | Argues each hypothesis is trivial/known/dead-end/insufficiently-wild; verifies citations; parks high-severity HYPs |
| `design` | `experiment-designer` (primary) | Opus | One `ExperimentPlan` per surviving HYP (≥3 seeds, matched-budget baseline, ≤30min compute) |
| `run` | `experiment-runner` | Sonnet | Materializes code, runs sanity gate then full sweep; emits `ExperimentResult` (`pass`/`fail`/`crash`); auto-ablates on pass |
| `critique` | `critic` (validity) | Opus | Reviews each `ExperimentResult` for threats to validity, baseline parity, statistical sins |
| `write` | `paper-writer` | Opus | Section-by-section: outline → abstract → intro → related-work → method → experiments → discussion |
| `final` | — (orchestrator) | — | Stitches `paper-vFINAL.md`; renders PDF if pandoc + a TeX engine are available |

### Three feedback loops

The orchestrator is not strictly forward — failed work loops back automatically.

| Loop | Trigger | Action | Cap (env var, default) |
|------|---------|--------|-----------------------|
| **Idea retreat** | After `screen`, `< MIN_WILD_HYPOTHESES` survive the wildness bar | Wipe checkpoints from `expand`; bump `idea_cycle`; re-run with parked-HYPs context | `AUTOLAB_MAX_IDEA_CYCLES=3` |
| **Experiment retreat** | After `critique`, no primary `ExperimentResult.status == "pass"` | Park failed HYPs; wipe from `survey`; bump `cycle`; re-run with failure context | `AUTOLAB_MAX_CYCLES=5` |
| **Crash retry** | After `run`, only `status=crash` for a plan | Re-invoke the runner with debug-fix prompt | `AUTOLAB_MAX_CRASH_RETRIES=2` per plan (on top of the runner's own 2 internal retries) |

State for all three loops lives in `projects/<id>/thread/cycles.json`.

### Subagents

| Skill | Role | Model |
|-------|------|-------|
| `idea-expander` | Seed Idea → Hypotheses (cross-domain transplant + gap-fill) | Sonnet |
| `literature-scout` | Pull related work via HF papers + arXiv + Semantic Scholar | Sonnet |
| `novelty-checker` | Fuzzy-title verify each Hypothesis vs LitFindings | Haiku |
| `experiment-designer` | Emit ExperimentPlan (≥3 seeds + matched-budget baseline) | Opus |
| `experiment-runner` | Sanity-gate + run + log; auto-ablate on pass; failure-analysis retry | Sonnet |
| `critic` | `boredom` / `validity` / `failure-analysis` modes | Opus / Haiku |
| `paper-writer` | Section-by-section, only verified citations; pastes pre-rendered tables | Opus |

Plus the bundled `huggingface-papers` skill (used by literature-scout, novelty-checker).

### Wildness bar

`expand` and `gap-fill` prompts inject explicit wildness criteria. Every Hypothesis must satisfy ≥1 ticket and name it in the body:

- **W1** — Cross-domain transplant from a NON-ML field (neuroscience, biology, physics, control theory, evolutionary theory, economics, linguistics, signal processing, statistics-beyond-ML, chemistry, statistical mechanics). RL→supervised, vision→NLP do **not** count — too close.
- **W2** — Explicitly contradicts a textbook claim. State the claim verbatim, then your counter-claim.
- **W3** — Measure something nobody has measured at meaningful scale.
- **W4** — Regime swap. Predict what changes when scale, data quality, modality, or compute is 100× or 0.01× the standard.

The boredom critic is calibrated to allow ~1-in-3 hypotheses through. Failures cascade into the idea retreat loop above.

### Per-project layout

```
projects/<id>/
├── thread/
│   ├── log.jsonl            # append-only event stream (one record per artifact)
│   ├── INDEX.md             # human-readable index, regenerated by tools/refresh_indexes.py
│   ├── cycles.json          # idea/experiment retreat state + crash retry counters
│   └── checkpoints/         # one <phase>.json per completed phase
├── thoughts/                # one MD per artifact id (long-form companion to log.jsonl)
├── papers/                  # fetched arxiv markdown + INDEX.md
├── experiments/<EXP-id>/
│   ├── code/run.py          # runner-written; sanity-gated; multi-seed
│   ├── runs/<ts>.log        # one log per invocation
│   ├── result.json          # canonical metrics (mean, stddev, n_seeds, per-seed)
│   └── repro.sh             # executable: recreates the run from scratch
├── drafts/
│   ├── paper-vFINAL.md      # assembled paper with auto-injected results tables
│   └── citations.bib        # verified citations only
├── ideas/parking_lot.md     # parked HYPs (failed boredom/validity or experiment retreat)
└── logs/
    ├── orchestrator.log     # phase begin/end + every call_claude
    └── cost_ledger.tsv      # 8-col token ledger (see below)
```

## Quality gates (default-on)

- **Pre-registered predictions** — every Hypothesis commits to a numeric `prediction_metric` / `prediction_threshold` / `prediction_direction` before resources are spent.
- **Wildness ticket** — expand/gap-fill must name a W1-W4 ticket per hypothesis; boredom critic enforces.
- **Cross-domain ideation** — at least one hypothesis per `expand` round must import from a non-ML field.
- **Multi-seed + matched-budget baseline** — every plan ships ≥3 seeds and a baseline with the same `compute_budget_minutes`; runner rejects plans missing either.
- **Sanity gate** — every model must overfit a 32-example subset before the main run, or the experiment aborts.
- **Auto-ablation** — every passing experiment triggers exactly one ablation isolating the proposed mechanism.
- **Failure analysis** — between failed retries, the critic explains why before the runner patches; up to 2 in-skill + `MAX_CRASH_RETRIES` orchestrator-level attempts.
- **Reproducibility envelope** — `experiments/<id>/repro.sh` captures seeds, code hash, env hash, command line.
- **Token ledger** — `logs/cost_ledger.tsv` rows per skill invocation: timestamp, phase, skill, model, input_tokens (fresh), cache_creation_tokens, cache_read_tokens, output_tokens. USD is intentionally not tracked; runs go until you stop them or hit a retreat cap.
- **Persistent idea bank** — un-pursued and parked hypotheses go to `ideas/parking_lot.md` and survive across runs (`./resume --resume-from-bank`).
- **Deterministic results tables** — `phase_final` injects a markdown summary table + per-experiment detail tables (proposed vs baseline, mean ± stddev, threshold, status) at the top of the Experiments section. The paper-writer is also given the same block to paste verbatim, so prose is anchored to canonical numbers.

## Dashboard

```bash
uv run python tools/dashboard.py          # http://127.0.0.1:8765
```

Auto-refreshes every 3s. No DB; reads directly from `projects/<id>/`. Shows:

- **Sidebar** — every project with live/stale dot, current phase, total tokens, last activity.
- **Live banner** — current phase, idea/experiment cycle, in-flight `claude -p` subprocesses (click to expand).
- **Phase pills** — done (green), running (pulsing amber), upcoming (gray).
- **Stat strip** — `tokens in · tokens out · cache hit % · claude calls`.
- **Active work** — Hypotheses still alive (not parked) and ExperimentPlans still in flight (no terminal result), with status badges.
- **Thread events** — feed of typed artifact emissions with per-type decision summaries (claim + prediction for HYP, status + notes for RES, severity + concerns for CRIT, …).
- **Token histograms** — per-phase and per-model, with stacked input bars (fresh / cache write / cache hit) and output bars.
- **Recent calls** — last 15 `claude -p` invocations with cache breakdown.
- **Drafts** — click `paper-vFINAL.md` to preview inline.
- **Thoughts**, **parking lot**, **papers index** — collapsed by default; click to expand.

## Configuration

All env vars are optional.

| Variable | Default | Effect |
|----------|---------|--------|
| `AUTOLAB_PROJECT` | (set by `./start`/`./resume`) | Which project subdir tools resolve under |
| `AUTOLAB_MAX_CYCLES` | `5` | Max experiment retreats per project (0 = unbounded) |
| `AUTOLAB_MAX_IDEA_CYCLES` | `3` | Max idea retreats per project |
| `AUTOLAB_MIN_WILD_HYPOTHESES` | `2` | Min HYPs that must survive screen to advance to design |
| `AUTOLAB_MAX_CRASH_RETRIES` | `2` | Orchestrator-level crash retries per plan (on top of the runner's 2 internal) |

Stop conditions are now: `final.json` checkpoint exists, `STOP` file at repo root, or you Ctrl+C. There is no dollar budget cap.

## Output: paper

`phase_final` writes `drafts/paper-vFINAL.md`. Re-assemble it without re-running the orchestrator:

```bash
uv run python tools/finalize.py --project <id>
```

## Setup

```bash
cd /Users/davis/Documents/code/autolab
uv sync
```

**Framework.** On Apple Silicon, MLX is installed by default and runs experiments on the unified-memory GPU + Neural Engine. The `experiment-designer` skill is wired to use `framework="mlx"` and the orchestrator injects a runtime probe of `mlx.default_device()` into each design prompt so the LLM knows MLX is available without inferring it. On non-Apple-Silicon hosts MLX is silently skipped (PEP 508 marker on the dep) and the designer falls back to PyTorch CPU. To opt into PyTorch as well: `uv sync --extra torch`.

**Authentication.** Claude Code subscription OAuth works out of the box. Run `claude login` in a regular terminal first; the orchestrator's subprocess inherits the on-disk credentials (it explicitly strips host-injected `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` / `CLAUDE_CODE_OAUTH_TOKEN` so you can run `./start` from anywhere — even from inside a Claude Code session).

## Verification (smoke)

```bash
./start --idea "investigate whether layer-wise learning rates help small MLPs on MNIST"
```

Expect after ~15-30 min:
- `projects/<slug>-<date>/thread/log.jsonl` populated across artifact types: Idea, Hypothesis, LitFinding, Critique, ExperimentPlan, ExperimentResult, Citation, DraftSection
- `papers/` has ≥5 fetched markdown copies
- `experiments/EXP-001/runs/` has logs + `result.json` with mean ± stddev
- `experiments/EXP-001/repro.sh` exists and is executable
- `drafts/paper-vFINAL.md` has all six numbered sections with a Results Summary table at the top of Experiments
- `drafts/citations.bib` contains only `verified=true` citations
- `logs/cost_ledger.tsv` shows per-phase token counts (8-column schema)

## Design notes

- **Process boundary = context boundary.** Each phase is a fresh `claude -p` call. No transcript carryover. Compaction is a fallback, not a strategy.
- **Read-by-handle.** Subagents read `thread/INDEX.md` first, then only `Read` the specific `thoughts/<id>.md` files they need.
- **Append-only.** Subagents never edit prior thread/thoughts entries; corrections go in new Critique artifacts.
- **Deterministic anchors.** Numbers in the paper come from `result.json`, not LLM prose. Tables are rendered programmatically and pasted by the paper-writer (with an assembly-time safety net if it forgets).
- **Loops over filters.** Idea retreat doesn't just discard boring HYPs — it forces the generator to try wilder. Experiment retreat doesn't just write a negative-result paper — it loops back to find new hypotheses. Both cap to bound the worst case.

## Inspirations

`autogolf-mlx` (loop pattern, program.md, idle watchdog), Sakana AI Scientist v2 (BFTS), Co-STORM (typed shared artifact > chat log), Anthropic multi-agent research system (orchestrator-worker, prescriptive delegation), Agent Laboratory (phase checkpoints), PaperOrchestra (two-phase citation grounding).
