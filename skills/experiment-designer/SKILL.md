---
name: experiment-designer
description: Convert a Hypothesis into a runnable ExperimentPlan with multi-seed setup, matched-budget baseline, and a code skeleton. MLX-first, PyTorch CPU fallback. Use when the orchestrator runs the `design` phase, or when generating an auto-ablation follow-up.
---

# experiment-designer

## Objective

For a target `Hypothesis`, produce one minimal `ExperimentPlan` that can validate or refute it on local hardware in under the compute budget. Plans must include ≥3 seeds and a matched-budget baseline; otherwise the runner will reject them.

## Modes

- `mode=primary` — design the main experiment that tests the hypothesis directly.
- `mode=ablation` — given an `ExperimentPlan` and its passing `ExperimentResult`, design a follow-up plan that *removes or inverts the proposed mechanism*. The ablation must run at the same scale as the main experiment.

## Inputs

- The target id from the orchestrator prompt (`HYP-<id>` for primary, `EXP-<id>` for ablation)
- `thoughts/<id>.md` for that target
- Any LitFindings cited by the target (for prior-art-informed design choices)

## Outputs

A single `ExperimentPlan` artifact via `python -m autolab.append_artifact`. Required fields:
- `hypothesis_id` — the HYP id this tests
- `dataset` — string: the HuggingFace dataset identifier (e.g. `"mnist"`, `"cifar10"`, `"wikitext"`, `"glue/sst2"`, `"ag_news"`, `"imdb"`). Must be a real dataset loadable via `load_dataset(name)`.
- `framework` — **`"mlx"` is the default and strongly preferred** (Apple Silicon GPU + Neural Engine, ~5-10× faster than torch CPU). Use `"torch"` ONLY if (a) the orchestrator's prompt explicitly says `mlx unavailable`, or (b) you need a specific op that MLX genuinely lacks (rare for MLP / small transformer / CNN work — check `mlx.core` and `mlx.nn` first).
- `model_spec` — JSON object describing architecture (e.g. `{"type":"mlp","depths":[64,32],"activation":"relu"}`)
- `metrics` — JSON list of metric names matching the hypothesis's `prediction_metric` plus any auxiliaries
- `seeds` — JSON list of ≥3 distinct integers (e.g. `[0, 1, 2]`)
- `baseline_spec` — JSON object: `{"name":"<name>","model_spec":..,"hyperparams":..,"compute_budget_minutes":<same as proposed>}` matched to the proposed run's compute budget
- `compute_budget_minutes` — int (max 30)
- `code_skeleton` — string (full Python, sufficient to run end-to-end after the runner fills in dataset paths)
- `is_ablation` — bool (false for primary, true for ablation)

## Tools

- `Read` — to inspect Hypothesis + LitFinding bodies
- `Bash` — to invoke `python -m autolab.append_artifact`

## Recommended model

`fable-5`

## Procedure (mode=primary)

1. Read the target Hypothesis. Note `prediction_metric`, `prediction_threshold`, `prediction_direction`.
2. Pick a real-world dataset from HuggingFace Hub that can plausibly reveal the predicted effect. **Do NOT generate synthetic data or use toy/fake datasets.** Use the HuggingFace Datasets library (`from datasets import load_dataset`) to pull established benchmarks with proper train/eval splits. Choose the smallest real dataset that is sufficient — e.g.:
   - **Classification:** `mnist`, `cifar10`, `ag_news`, `imdb`, `sst2` (via `glue`), `emotion`
   - **Language modeling:** `wikitext` (wikitext-2-raw-v1), `tiny_shakespeare`, `ptb_text_only`
   - **Sequence tasks:** `conll2003`, `squad`, `xsum`
   - **Tabular:** `scikit-learn/iris`, `mstz/heart_failure`
   - Or any other HuggingFace dataset appropriate to the hypothesis.

   Use the HuggingFace Dataset Viewer API (https://datasets-server.huggingface.co) to verify the dataset exists and inspect its structure (splits, columns, sizes) before committing to it. Specifically:
   - Check available configs/splits: `GET /splits?dataset={dataset_name}`
   - Preview rows: `GET /first-rows?dataset={dataset_name}&config={config}&split={split}`
   - Check size: `GET /size?dataset={dataset_name}`

3. Decide framework:
   - **Default to `mlx`.** It's installed and runs on the Apple Silicon GPU. Use `import mlx.core as mx` and `import mlx.nn as nn` (and `import mlx.optimizers as optim`). Seed via `mx.random.seed(seed)`.
   - Switch to `torch` ONLY if the orchestrator's prompt says `mlx unavailable`, OR you've checked `mlx.core` / `mlx.nn` and the op you need genuinely isn't there. Don't switch out of habit — MLX covers MLP, transformer, CNN, RNN, attention, layernorm, dropout, AdamW, gradient clipping, mixed precision, etc.
   - **Never use torch CUDA.** Apple Silicon has no CUDA; if you must use torch, it's CPU-only.
4. Specify a baseline with matched compute. The baseline is whatever the hypothesis is implicitly compared against (uniform LR vs per-layer LR, etc.). The baseline's compute_budget_minutes must equal the proposed run's.
5. Decide seeds: at least 3 distinct ints. More if the predicted effect is small (e.g. 5 seeds for a 0.1pp prediction).
6. Estimate compute: total wall time ≈ seeds × (proposed minutes) + seeds × (baseline minutes). Must fit in `compute_budget_minutes ≤ 30`. If it doesn't, scale the model down.
7. Write a `code_skeleton` — a complete Python file the runner can drop into `experiments/<EXP-id>/code/run.py`. The skeleton should:
   - Accept `--seed <int>`, `--config <baseline|proposed>`, `--out <path>` CLI args
   - **Load data via `from datasets import load_dataset`** — use the real train/test splits from HuggingFace. Do NOT synthesize, generate, or fake data. The dataset download is cached automatically to `~/.cache/huggingface/datasets/`.
   - Apply appropriate preprocessing (tokenization, normalization, reshaping) to the real dataset
   - Train, evaluate, and write `{seed, config, metric: value, wall_seconds}` to JSON-Lines on stdout
   - Use deterministic seeding (`mx.random.seed`, `torch.manual_seed`, `numpy.random.seed`)
   - Network calls for dataset download are allowed (HuggingFace is on the allowlist); the `datasets` library caches after first download
8. Emit the plan via `python -m autolab.append_artifact --type ExperimentPlan ...`. The id printed (e.g. `EXP-003`) is the runner's working dir name.

## Procedure (mode=ablation)

1. Read the target `ExperimentPlan` (the primary that passed) and its `ExperimentResult`.
2. Identify the *proposed mechanism* — the single architectural / optimizer / data choice that the hypothesis attributes the win to.
3. Design an ablation plan that removes or inverts ONLY that one mechanism, holding everything else fixed:
   - Same dataset, model class (modulo the ablated piece), seeds, compute budget
   - `is_ablation=true`
   - `parent_ids=[<EXP-primary-id>]`
4. Code skeleton should be a minimal diff of the primary skeleton (e.g. set per-layer LRs to a constant), not a fresh implementation.
5. Emit via `python -m autolab.append_artifact`.

## Boundaries

- **Do not invoke other skills.**
- **Do not run the experiment.** That is `experiment-runner`.
- **Do not propose plans without seeds + baseline.** The runner rejects them and the orchestrator parks the hypothesis.
- **Do not propose compute_budget_minutes > 30.** Scale down the model or dataset until it fits.
- **Do not generate synthetic or fake datasets.** Always use real datasets from HuggingFace Hub via `load_dataset()`. The `datasets` library handles caching — first download hits the network (huggingface.co is on the allowlist), subsequent runs use the cache.
- **Do not use random/dummy data as a substitute for real evaluation.** If you need a small dataset, pick a small *real* one (e.g., `iris`, `sst2`, `mnist`), don't fabricate one with `numpy.random`.

## Stdout contract

```
phase=design status=ok mode=<primary|ablation> new_ids=EXP-003
```
