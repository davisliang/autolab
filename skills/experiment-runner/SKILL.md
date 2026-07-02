---
name: experiment-runner
description: Materialize an ExperimentPlan into runnable code under experiments/<id>/code/, run a sanity gate, then execute multi-seed runs and the matched baseline. Emits ExperimentResult with mean ± stddev. Use when the orchestrator runs the `run` phase.
---

# experiment-runner

## Objective

Take a single `ExperimentPlan`, materialize its code skeleton into `experiments/<EXP-id>/code/`, run the sanity gate, then execute the proposed and baseline conditions across all seeds, and emit one `ExperimentResult` artifact summarizing mean ± stddev. Generate `repro.sh` for reproducibility.

## Inputs

- The target id from the orchestrator prompt (e.g. `EXP-003`)
- `thoughts/EXP-003.md` (the plan body, with the `code_skeleton` field)

## Outputs

- `experiments/<EXP-id>/code/run.py` (and any helpers)
- `experiments/<EXP-id>/runs/<timestamp>.log` per invocation
- `experiments/<EXP-id>/result.json` — canonical metrics dict
- `experiments/<EXP-id>/repro.sh` — executable script that recreates the run from scratch
- One `ExperimentResult` artifact via `python -m autolab.append_artifact`

## Tools

- `python -m autolab.run_experiment` — the canonical runner. It handles sanity gate, multi-seed execution, baseline execution, timeout enforcement, log capture, and `repro.sh` emission. **Always use it; do not invoke `python` or `uv run` directly to run the experiment.**
- `Read`, `Edit`, `Write` — only inside `experiments/<EXP-id>/`
- `Bash` — for `python -m autolab.run_experiment` and `python -m autolab.append_artifact` invocations

## Recommended model

`fable-5`

## Procedure

1. Read the `ExperimentPlan`. Verify it has `seeds: [≥3]` and `baseline_spec` populated. If either is missing, abort with a `Critique` (severity=high) and do not run.
2. Materialize the code:
   - `mkdir -p experiments/<EXP-id>/code experiments/<EXP-id>/runs`
   - Write the `code_skeleton` to `experiments/<EXP-id>/code/run.py`
   - If the plan provides additional helper files, write each to `experiments/<EXP-id>/code/`
   - **Note:** The code skeleton will use `from datasets import load_dataset` to pull real datasets from HuggingFace Hub. This requires network access on first run (cached thereafter at `~/.cache/huggingface/datasets/`). This is expected and allowed.
3. Sanity gate:
   ```
   python -m autolab.run_experiment --plan-id <EXP-id> --sanity
   ```
   This trains on 32 examples for 60 s and asserts train loss decreases by ≥50%.
   - If sanity fails: emit a `Critique` (mode=validity, severity=high, target=<EXP-id>, proposed_fix=<analysis>) and stop. The plan is parked.
4. Main run + baseline:
   ```
   python -m autolab.run_experiment --plan-id <EXP-id> --run
   ```
   The tool runs all seeds × {proposed, baseline} sequentially with per-run timeouts and writes one log per invocation. It aggregates into `result.json` with `{metric: {mean, stddev, n_seeds, per_seed: [...]}}` for each condition.
5. On crash: the tool returns non-zero. Up to `max_debug_depth=2`:
   a. Read the failing `runs/<latest>.log`
   b. Invoke `python -m autolab.append_artifact --type Critique --mode failure-analysis --target-id <EXP-id> --severity med --concerns "<short>" --proposed_fix "<patch>"`
   c. Apply the fix to `experiments/<EXP-id>/code/run.py` via `Edit`
   d. Re-run with `--run`
   e. If still failing after 2 retries: emit a final `Critique` (severity=high, mode=validity) and stop.
6. On success:
   - Emit `ExperimentResult` (status=pass if `metrics.mean[prediction_metric]` exceeds the hypothesis threshold in the predicted direction; else status=fail)
   - The orchestrator handles the auto-ablation trigger; you do not invoke `experiment-designer` directly.
7. Generate `experiments/<EXP-id>/repro.sh` automatically (the runner does this; verify it exists and is executable).

## Boundaries

- **Do not write outside `experiments/<EXP-id>/`** at the experiment-code level (top-level write roots from `program.md` still apply for thread/papers/thoughts/drafts).
- **Do not invoke other skills.**
- **Do not skip the sanity gate.** Even one-line code changes need it.
- **Apply the minimal fix during debug retries.** Change only what the failure requires; don't refactor, rename, or restructure working code between attempts.
- **Do not modify other experiments' code or results.**
- **Do not increase compute past `compute_budget_minutes`.** The tool enforces a hard timeout.

## Stdout contract

```
phase=run status=<pass|fail|crash> plan_id=EXP-003 new_ids=RES-005[,CRIT-009]
```

## Worked example

```
python -m autolab.run_experiment --plan-id EXP-003 --sanity
# -> "sanity_pass=true delta_loss=0.71"
python -m autolab.run_experiment --plan-id EXP-003 --run
# -> writes experiments/EXP-003/result.json
python -m autolab.append_artifact --type ExperimentResult --parent EXP-003 \
  --author experiment-runner \
  --summary "MNIST MLP per-layer LR vs uniform: +0.42pp val_acc (n=3)" \
  --field plan_id=EXP-003 \
  --field status=pass \
  --field metrics='{"val_accuracy":{"mean":97.42,"stddev":0.18,"n_seeds":3}}' \
  --field runs_dir=experiments/EXP-003/runs
```
