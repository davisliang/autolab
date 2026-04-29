# autolab

Autonomous research-loop. Point it at a one-line idea, walk away, come back to a paper draft (Markdown) with verified citations, deterministic results tables, and reproducible experiments. Each run lives in its own project directory; subagents communicate through a typed shared thread on disk — never via chat — referencing each other by stable artifact ID.

## Repository layout

```
.
├── autolab/                  # the python package — core build
│   ├── __init__.py
│   ├── orchestrator.py       # phase pipeline driver
│   ├── paths.py              # project-scoped path helpers
│   ├── results_tables.py     # deterministic markdown table generator
│   ├── append_artifact.py    # append-only thread/log writer
│   ├── refresh_indexes.py    # regenerate thread/papers/projects INDEX.md
│   ├── fetch_paper.py        # cache HF/arXiv paper markdown
│   ├── verify_citation.py    # fuzzy claim↔paper match
│   ├── run_experiment.py     # sanity gate + multi-seed runner
│   ├── finalize.py           # re-assemble paper-vFINAL.md
│   ├── idle_continue.py      # CPU-idle watchdog
│   └── dashboard/            # read-only progress dashboard
├── scripts/                  # entry shell scripts
│   ├── start                 # new project on a fresh idea
│   ├── resume                # continue an existing project
│   └── continue_loop.sh      # used by idle_continue
├── prompts/program.md        # system prompt loaded into every claude -p call
├── skills/                   # claude skill definitions (one dir per subagent)
├── tests/                    # pytest suite for pure helpers + structural invariants
├── projects/                 # per-run output (gitignored)
├── pyproject.toml            # package metadata + dev deps + tool config
├── .pre-commit-config.yaml   # black + ruff + pytest, runs on git commit
└── README.md                 # this file
```

## Quickstart

### 1. Prerequisites

- **Python 3.11+** (3.11–3.13 are tested).
- **[uv](https://docs.astral.sh/uv/)** for dependency management. On macOS: `brew install uv`.
- **[Claude Code](https://claude.com/product/claude-code)** CLI on `$PATH`. Run `claude login` in a regular terminal once — the orchestrator inherits the on-disk OAuth credentials. (Subscription auth works out of the box; an `ANTHROPIC_API_KEY` is **not** required and will be stripped from the subprocess env.)
- **Apple Silicon optional**: MLX is installed on M-series Macs by default and used for experiment runs. On other hosts, `uv sync --extra torch` enables PyTorch CPU as the fallback.

### 2. Install

```bash
git clone <this-repo> autolab
cd autolab
uv sync                       # core deps
uv sync --group dev           # also install pytest / black / ruff / pre-commit
uv run pre-commit install     # wire up git hooks (optional, recommended)
```

Smoke-check the install:

```bash
uv run pytest                 # 49 tests, < 1s
```

### 3. First run via `example.sh`

[`example.sh`](example.sh) is the recommended onramp — it shows every CLI flag and tunable env var in one place. Copy it, edit the seed idea and any knobs you want to override, then run:

```bash
$EDITOR example.sh            # change IDEA="..." and any AUTOLAB_* defaults
bash example.sh
```

The script will:
1. Create a fresh project directory under `projects/<slug>-<YYYYMMDD>/`.
2. Print the env var values it will use.
3. `exec` into `scripts/start`, which drives the full phase pipeline (`seed → expand → survey → gap-fill → screen → design → run → critique → write → final`).

While it runs, watch progress in another terminal:

```bash
uv run python -m autolab.dashboard.server          # http://127.0.0.1:8765
```

When it finishes (~15–30 min for the default settings), the deliverable lives at:

```
projects/<your-slug>-<date>/drafts/paper-vFINAL.md
```

with verified citations in `citations.bib`, per-experiment `result.json`, and a reproducibility shell at `experiments/<EXP-id>/repro.sh`.

### 4. Stopping and resuming

```bash
# stop a running orchestrator (any of these works)
Ctrl+C                                          # in its terminal
touch STOP                                      # graceful, at the next phase boundary
pkill -f autolab.orchestrator                   # nuclear

# resume an existing project
scripts/resume                                  # interactive picker
scripts/resume --project <id>                   # by id
scripts/resume --list                           # print the projects table
scripts/resume --project <id> --resume-from-bank   # pop next parked HYP from ideas/parking_lot.md
```

### 5. Direct invocation (advanced)

If you'd rather skip the `example.sh` wrapper, call `scripts/start` directly:

```bash
# inline argv (short ideas only — avoid embedded apostrophes/quotes)
scripts/start --idea "investigate whether layer-wise learning rates help small MLPs on MNIST"

# from a file (recommended for long, multi-paragraph ideas)
scripts/start --idea-file my-idea.txt

# from stdin
scripts/start --idea-stdin <<'EOF'
multi-line idea, apostrophes/quotes fine
EOF

# also seed an extra Hypothesis on resume
scripts/resume --project <id> --hypothesis "user-supplied claim"
```

Tunable env vars (full list in [Configuration](#configuration)) — set them inline or in `example.sh`:

```bash
AUTOLAB_MAX_CYCLES=10 AUTOLAB_MIN_WILD_HYPOTHESES=3 scripts/start --idea "..."
```

## Architecture

The bot is a `claude` CLI loop. Each phase is a fresh headless `claude -p` subprocess; subagents are skills under `skills/<name>/SKILL.md` that auto-load from cwd. Every run creates one project directory under `projects/<slug>-<YYYYMMDD>[-N]/` containing its own thread, papers, thoughts, experiments, drafts, and logs.

### Phase pipeline

```
seed → expand → survey → gap-fill → screen → design → run → critique → write → final → review
                              ↑                                  │                       │
                              │  experiment retreat (no pass)    │                       │
                              └──────────────────────────────────┘                       │
                  ↑              │                                                       │
                  │ idea retreat │                                                       │
                  │ (too boring) │                                                       │
                  └──────────────┘                                                       │
                                                                                         │
              ┌──────────────────────────────────────────────────────────────────────────┘
              │ review loopback (committee says major_revision → target_phase)
              ▼
         survey | design | run | critique | write | final
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
| `write` | `paper-writer` | Opus | Section-by-section: outline → abstract → intro → related → background → data/models → method → experiments → discussion → conclusion → broader-impact → reproducibility |
| `final` | `paper-polisher` | Opus | Stitches `paper-vFINAL.md`, then runs a polish pass that re-reads the whole paper, fills any `_(missing)_` sections, tightens weak prose, and enforces consistency between the intro contributions and the experiments table. Pre-polish version is kept at `paper-vFINAL.pre-polish.md` for diffing. |
| `review` | `committee-reviewer` ×3 (parallel) | Opus | A 3-persona committee (methodologist, domain-expert, clarity-reviewer) reads the polished paper plus the artifact thread and emits one `Review` per persona. Recommendations aggregate to `accept` (ship), `minor_revision` (ship; advisory), or `major_revision` → loop back to a reviewer-named `target_phase` (one of `survey`, `design`, `run`, `critique`, `write`, `final`). |

### Four feedback loops

The orchestrator is not strictly forward — failed work loops back automatically.

| Loop | Trigger | Action | Cap (env var, default) |
|------|---------|--------|-----------------------|
| **Idea retreat** | After `screen`, `< MIN_WILD_HYPOTHESES` survive the wildness bar | Wipe checkpoints from `expand`; bump `idea_cycle`; re-run with parked-HYPs context | `AUTOLAB_MAX_IDEA_CYCLES=3` |
| **Experiment retreat** | After `critique`, no primary `ExperimentResult.status == "pass"` | Park failed HYPs; wipe from `survey`; bump `cycle`; re-run with failure context | `AUTOLAB_MAX_CYCLES=5` |
| **Crash retry** | After `run`, only `status=crash` for a plan | Re-invoke the runner with debug-fix prompt | `AUTOLAB_MAX_CRASH_RETRIES=2` per plan (on top of the runner's own 2 internal retries) |
| **Review loopback** | After `review`, any committee persona returns `recommendation=major_revision` with a valid `target_phase` | Wipe checkpoints from the earliest requested `target_phase` forward; bump `review_cycle`; re-run with the prior-round Review artifacts in context | `AUTOLAB_MAX_REVIEW_CYCLES=2` |

State for all four loops lives in `projects/<id>/thread/cycles.json` (structured) and `projects/<id>/thread/history.md` (groomed prose narrative).

### Run history (cross-loop context)

Every retreat / loopback (experiment retreat, idea retreat, review loopback) appends one deterministically-templated Markdown section to `projects/<id>/thread/history.md`. Each section names what was tried, the parked artifact ids (HYP-/REV-/CRIT-), the specific concerns that drove the loopback, and an explicit `**Next:**` directive for the re-run skill.

Every phase that may run as part of a loopback (`expand`, `survey`, `gap-fill`, `screen`, `design`, `run`, `critique`, `write`, the `final` polish pass, and `review` itself) injects this file's content as a `## RUN HISTORY (groomed, append-only)` block at the top of its prompt — so skills always see the cross-loop story in one place, with pointers to the raw artifacts they can `Read` for full bodies.

Compounding context: cycle 3 sees both cycle 1 and cycle 2's entries, in order. The block is capped at ~8000 chars per prompt; older entries are elided with a note pointing at the on-disk file. To watch the narrative grow live: `tail -f projects/<id>/thread/history.md`.

### Committee review (the `review` phase, in detail)

After `final` writes a polished paper, `phase_review` runs a NeurIPS-style program committee against it. The mechanics:

**1. Three reviewers in parallel.** `phase_review` dispatches three concurrent calls of the `committee-reviewer` skill, one per persona:

| Persona | Focus |
|---------|-------|
| `methodologist` | Experimental design, statistical validity, baseline parity, seed counts, ablation coverage, reproducibility envelope. Cross-checks claims in the paper against validity-mode `Critique` artifacts. |
| `domain-expert` | Novelty, contribution, related-work positioning. Are claims supported by experiments? Are obvious neighbors missing from `cite_pool`? |
| `clarity-reviewer` | Writing, structure, story. Is the introduction's contributions list 1-for-1 with the experiments headline table? Would a NeurIPS reviewer reading only Abstract + §1 + main table walk away with the right takeaway? |

Each reviewer reads the polished `paper-vFINAL.md`, the relevant artifact thread (Idea, Hypotheses, ExperimentResults, validity Critiques, *and prior Reviews if this is a re-review*), and `citations.bib`.

**2. Each persona emits one `Review` artifact** with these fields:

| Field | Values |
|-------|--------|
| `persona` | `methodologist` / `domain-expert` / `clarity-reviewer` |
| `recommendation` | `accept` / `minor_revision` / `major_revision` |
| `target_phase` | one of `survey`, `design`, `run`, `critique`, `write`, `final` (required only for `major_revision`) |
| `score_overall` | int 1–10 |
| `score_soundness` | int 1–10 |
| `score_novelty` | int 1–10 |
| `score_clarity` | int 1–10 |

Plus a markdown body with strengths, weaknesses, specific concerns (cited by section number and artifact id), and requested changes.

**3. Decision rules.** `review_loopback_check()` aggregates the three Reviews and chooses one of:

| Aggregate verdict | Action |
|---|---|
| All three say `accept` | **Ship.** Paper is done; orchestrator exits. |
| Any reviewer says `major_revision` with a valid `target_phase` | **Loop back.** Wipe checkpoints from the *earliest* requested `target_phase` forward, bump `review_cycle`, re-run from that phase. Prior Reviews stay in the thread so the next round of writers/designers/runners sees the feedback. |
| Mix of accept + minor (no valid major) | **Ship.** Minor revisions are advisory; the polish pass already ran inside `final`, so further changes would need a manual `--resume`. |
| Cap reached (`review_cycle >= AUTOLAB_MAX_REVIEW_CYCLES`) | **Ship unconditionally**, regardless of recommendations. |

**4. Is there a numeric pass threshold?** No, not at the orchestrator level. The decision is made on the categorical `recommendation` field; the four numeric scores are recorded for reference but never read by `review_loopback_check`. The `committee-reviewer` skill suggests a rubric to each reviewer (`score_overall ≥ 7` → accept, `5–6` → minor, `≤ 4` → major), but reviewers can override based on qualitative concerns. The effective ship condition is **3-for-3 unanimous accept** (or any non-major outcome at the cycle cap).

**5. Skipping the committee.** Set `AUTOLAB_SKIP_REVIEW=1` to bypass the phase entirely — the paper ships straight from `final`.

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
| `paper-polisher` | Final whole-paper pass: fills missing sections, improves clarity, enforces intro↔experiments consistency | Opus |
| `committee-reviewer` | Single-persona NeurIPS-style reviewer; emits one `Review` artifact (accept / minor / major + target_phase). Run 3× in parallel during `review` | Opus |

Plus the bundled `huggingface-papers` skill (used by `literature-scout`, `novelty-checker`).

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
│   ├── INDEX.md             # human-readable index, regenerated by python -m autolab.refresh_indexes
│   ├── cycles.json          # idea/experiment/review retreat state + crash retry counters
│   ├── history.md           # groomed cross-loop narrative (one section per loopback)
│   └── checkpoints/         # one <phase>.json per completed phase
├── thoughts/                # one MD per artifact id (long-form companion to log.jsonl)
├── papers/                  # fetched arxiv markdown + INDEX.md
├── experiments/<EXP-id>/
│   ├── code/run.py          # runner-written; sanity-gated; multi-seed
│   ├── runs/<ts>.log        # one log per invocation
│   ├── result.json          # canonical metrics (mean, stddev, n_seeds, per-seed)
│   └── repro.sh             # executable: recreates the run from scratch
├── drafts/
│   ├── paper-vFINAL.md           # assembled and polished paper (see `final` phase)
│   ├── paper-vFINAL.pre-polish.md  # pre-polish backup, kept for diffing
│   └── citations.bib              # verified citations only
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
- **Persistent idea bank** — un-pursued and parked hypotheses go to `ideas/parking_lot.md` and survive across runs (`scripts/resume --resume-from-bank`).
- **Deterministic results tables** — `phase_final` injects a markdown summary table + per-experiment detail tables (proposed vs baseline, mean ± stddev, threshold, status) at the top of the Experiments section. The paper-writer is also given the same block to paste verbatim, so prose is anchored to canonical numbers.

## Dashboard

```bash
uv run python -m autolab.dashboard.server          # http://127.0.0.1:8765
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
| `AUTOLAB_PROJECT` | (set by `scripts/start`/`scripts/resume`) | Which project subdir tools resolve under |
| `AUTOLAB_MAX_CYCLES` | `5` | Max experiment retreats per project (0 = unbounded) |
| `AUTOLAB_MAX_IDEA_CYCLES` | `3` | Max idea retreats per project |
| `AUTOLAB_MIN_WILD_HYPOTHESES` | `2` | Min HYPs that must survive screen to advance to design |
| `AUTOLAB_MAX_CRASH_RETRIES` | `2` | Orchestrator-level crash retries per plan (on top of the runner's 2 internal) |
| `AUTOLAB_MAX_REVIEW_CYCLES` | `2` | Max committee-review loopbacks before shipping the paper unconditionally |
| `AUTOLAB_SKIP_POLISH` | unset | If set (any value), skip the polish pass at the end of `phase_final`. The unpolished assembled paper is still written. |
| `AUTOLAB_SKIP_REVIEW` | unset | If set, skip the `review` phase entirely. The paper ships straight from `final`. |

Stop conditions: terminal-phase checkpoint exists (`review.json` once the committee has run, or `final.json` when `AUTOLAB_SKIP_REVIEW=1`), `STOP` file at repo root, or you Ctrl+C. There is no dollar budget cap.

## Output: paper

`phase_final` writes `drafts/paper-vFINAL.md`. Re-assemble it without re-running the orchestrator:

```bash
uv run python -m autolab.finalize --project <id>
```

## Framework and auth details

**Framework.** On Apple Silicon, MLX is installed by default and runs experiments on the unified-memory GPU + Neural Engine. The `experiment-designer` skill is wired to use `framework="mlx"` and the orchestrator injects a runtime probe of `mlx.default_device()` into each design prompt so the LLM knows MLX is available without inferring it. On non-Apple-Silicon hosts MLX is silently skipped (PEP 508 marker on the dep) and the designer falls back to PyTorch CPU. To opt into PyTorch as well: `uv sync --extra torch`.

**Authentication.** Claude Code subscription OAuth works out of the box. Run `claude login` in a regular terminal first; the orchestrator's subprocess inherits the on-disk credentials (it explicitly strips host-injected `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` / `CLAUDE_CODE_OAUTH_TOKEN` so you can run `scripts/start` from anywhere — even from inside a Claude Code session).

## Development

The dev tools (pytest, black, ruff, pre-commit) live in the `dev` dependency group — see [Quickstart §2](#2-install) for install commands.

### Run tests

The `tests/` directory holds the pytest suite. It exercises pure helpers (`autolab.paths`, `autolab.results_tables`) and structural invariants of the orchestrator (phase ordering, NeurIPS section briefs, `phase_final` assembly order):

```bash
uv run pytest                       # all tests, quiet
uv run pytest -v                    # verbose
uv run pytest tests/test_paths.py   # one file
uv run pytest -k slugify            # by name
```

The full suite runs in well under a second. New code that's testable as a pure function should ship with tests in this directory.

### Lint and format

Black and ruff are both configured in `pyproject.toml`:

- `black` — formatter; line length 100.
- `ruff` — linter (E/F/W/I/B/UP rule sets); import-sorts and applies UP modernization fixes.

Run them manually:

```bash
uv run black tests/                 # format tests
uv run ruff check autolab/ tests/   # lint
uv run ruff check --fix autolab/    # apply auto-fixes
uv run ruff format autolab/         # ruff's own formatter
```

### Pre-commit hooks

`.pre-commit-config.yaml` runs four kinds of checks on every `git commit`:

1. **File hygiene** — trailing whitespace, EOF newline, valid YAML/TOML, no merge-conflict markers, no large files (>500 KB).
2. **`black`** — auto-formats staged Python files to match `pyproject.toml` settings.
3. **`ruff`** — lints + auto-fixes safe issues; runs `ruff format` after.
4. **`pytest`** — runs the full unit test suite via `uv run pytest -q tests/`. Commit fails if any test fails.

Install once after cloning (already covered in [Quickstart §2](#2-install)):

```bash
uv run pre-commit install
```

Subsequent commits will trigger the hooks automatically. To run all hooks against every file (e.g. after upgrading the config):

```bash
uv run pre-commit run --all-files
```

To bypass in an emergency only (don't make a habit of it):

```bash
git commit --no-verify
```

## Expected output

After a successful run (~15–30 min on the default settings) under `projects/<slug>-<date>/`:

- `thread/log.jsonl` populated across artifact types: Idea, Hypothesis, LitFinding, Critique, ExperimentPlan, ExperimentResult, Citation, DraftSection
- `papers/` has ≥5 fetched markdown copies
- `experiments/EXP-001/runs/` has logs + `result.json` with mean ± stddev
- `experiments/EXP-001/repro.sh` exists and is executable
- `drafts/paper-vFINAL.md` has all eleven NeurIPS-style sections (Abstract through Reproducibility) with a Results Summary table at the top of Experiments
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
