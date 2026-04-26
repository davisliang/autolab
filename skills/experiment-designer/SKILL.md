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

A single `ExperimentPlan` artifact via `tools/append_artifact.py`. Required fields:
- `hypothesis_id` — the HYP id this tests
- `dataset` — string (e.g. `"mnist"`, `"cifar10"`, `"shakespeare-char"`, `"sst2"`)
- `framework` — `"mlx"` (preferred on Apple Silicon) | `"torch"` (CPU fallback)
- `model_spec` — JSON object describing architecture (e.g. `{"type":"mlp","depths":[64,32],"activation":"relu"}`)
- `metrics` — JSON list of metric names matching the hypothesis's `prediction_metric` plus any auxiliaries
- `seeds` — JSON list of ≥3 distinct integers (e.g. `[0, 1, 2]`)
- `baseline_spec` — JSON object: `{"name":"<name>","model_spec":..,"hyperparams":..,"compute_budget_minutes":<same as proposed>}` matched to the proposed run's compute budget
- `compute_budget_minutes` — int (max 30)
- `code_skeleton` — string (full Python, sufficient to run end-to-end after the runner fills in dataset paths)
- `is_ablation` — bool (false for primary, true for ablation)

## Tools

- `Read` — to inspect Hypothesis + LitFinding bodies
- `Bash` — to invoke `tools/append_artifact.py`

## Recommended model

`opus-4-7`

## Procedure (mode=primary)

1. Read the target Hypothesis. Note `prediction_metric`, `prediction_threshold`, `prediction_direction`.
2. Pick the smallest dataset/model that can plausibly reveal the predicted effect (default: a tracked benchmark — MNIST MLP, tiny-shakespeare char-LM, or CIFAR10 small CNN).
3. Decide framework:
   - Default to `mlx` (Apple Silicon native).
   - Use `torch` if MLX lacks a required op or the experiment is purely CPU-friendly tabular work.
4. Specify a baseline with matched compute. The baseline is whatever the hypothesis is implicitly compared against (uniform LR vs per-layer LR, etc.). The baseline's compute_budget_minutes must equal the proposed run's.
5. Decide seeds: at least 3 distinct ints. More if the predicted effect is small (e.g. 5 seeds for a 0.1pp prediction).
6. Estimate compute: total wall time ≈ seeds × (proposed minutes) + seeds × (baseline minutes). Must fit in `compute_budget_minutes ≤ 30`. If it doesn't, scale the model down.
7. Write a `code_skeleton` — a complete Python file the runner can drop into `experiments/<EXP-id>/code/run.py`. The skeleton should:
   - Accept `--seed <int>`, `--config <baseline|proposed>`, `--out <path>` CLI args
   - Train, evaluate, and write `{seed, config, metric: value, wall_seconds}` to JSON-Lines on stdout
   - Use deterministic seeding (`mx.random.seed`, `torch.manual_seed`, `numpy.random.seed`)
   - Avoid network calls inside the run; datasets must be pre-cached or loaded from `~/.cache/...`
8. Emit the plan via `tools/append_artifact.py --type ExperimentPlan ...`. The id printed (e.g. `EXP-003`) is the runner's working dir name.

## Procedure (mode=ablation)

1. Read the target `ExperimentPlan` (the primary that passed) and its `ExperimentResult`.
2. Identify the *proposed mechanism* — the single architectural / optimizer / data choice that the hypothesis attributes the win to.
3. Design an ablation plan that removes or inverts ONLY that one mechanism, holding everything else fixed:
   - Same dataset, model class (modulo the ablated piece), seeds, compute budget
   - `is_ablation=true`
   - `parent_ids=[<EXP-primary-id>]`
4. Code skeleton should be a minimal diff of the primary skeleton (e.g. set per-layer LRs to a constant), not a fresh implementation.
5. Emit via `tools/append_artifact.py`.

## Boundaries

- **Do not invoke other skills.**
- **Do not run the experiment.** That is `experiment-runner`.
- **Do not propose plans without seeds + baseline.** The runner rejects them and the orchestrator parks the hypothesis.
- **Do not propose compute_budget_minutes > 30.** Scale down the model or dataset until it fits.
- **Do not cite uncached data sources.** All datasets must be available offline or via the network allowlist (huggingface.co/datasets).

## Stdout contract

```
phase=design status=ok mode=<primary|ablation> new_ids=EXP-003
```
