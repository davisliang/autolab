"""Markdown results-table generator.

Reads each ExperimentPlan/ExperimentResult and the corresponding
`experiments/<EXP-id>/result.json` to produce a deterministic markdown block
(summary table + per-experiment detail) that's pasted into the paper at the
top of the Experiments section.

Schema-tolerant: handles the canonical nested `{metrics: {proposed, baseline}}`
schema as well as flat schemas with `proposed_X` / `baseline_X` paired metrics
and standalone delta metrics like `cost_savings_pp_vs_X`.

Pure: no orchestrator imports, no AUTOLAB_PROJECT lookup. Caller passes the
already-parsed thread list and the experiments dir.
"""

from __future__ import annotations

import json
from pathlib import Path

# ---- formatting helpers ----------------------------------------------------


def fmt_num(v, sig: int = 4) -> str:
    """Compact numeric formatter: avoids scientific where possible, max sig figs."""
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f == 0:
        return "0"
    abs_f = abs(f)
    if abs_f >= 1000 or abs_f < 0.001:
        return f"{f:.{sig-1}e}"
    if abs_f >= 1:
        return f"{f:.{max(0, sig - len(str(int(abs_f))))}f}"
    return f"{f:.{sig}f}"


def is_stat_dict(v) -> bool:
    return isinstance(v, dict) and isinstance(v.get("mean"), (int, float))


def detect_proposed_baseline_pairs(metrics: dict) -> list[tuple[str, str, str]]:
    """Find proposed/baseline metric pairs by name convention.

    Looks for: `proposed_X` paired with `baseline_X` (or `X_proposed`/`X_baseline`).
    Returns [(base_name, proposed_key, baseline_key), ...].
    """
    pairs: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for k, v in metrics.items():
        if not is_stat_dict(v):
            continue
        for prefix in ("proposed_", "baseline_"):
            if k.startswith(prefix):
                base = k[len(prefix) :]
                other_prefix = "baseline_" if prefix == "proposed_" else "proposed_"
                other = other_prefix + base
                if other in metrics and is_stat_dict(metrics[other]) and base not in seen:
                    pairs.append((base, "proposed_" + base, "baseline_" + base))
                    seen.add(base)
        for suffix in ("_proposed", "_baseline"):
            if k.endswith(suffix):
                base = k[: -len(suffix)]
                other_suffix = "_baseline" if suffix == "_proposed" else "_proposed"
                other = base + other_suffix
                if other in metrics and is_stat_dict(metrics[other]) and base not in seen:
                    pairs.append((base, base + "_proposed", base + "_baseline"))
                    seen.add(base)
    return pairs


def pick_summary_metric(metrics: dict, pred_metric: str) -> str | None:
    """Choose one metric to show in the summary row. Priority:
    predicted metric > delta-like name > first stat metric."""
    if pred_metric and pred_metric in metrics and is_stat_dict(metrics[pred_metric]):
        return pred_metric
    delta_tokens = ("_vs_", "delta_", "_delta", "savings", "reduction", "improvement", "lift")
    for k, v in metrics.items():
        if is_stat_dict(v) and any(t in k.lower() for t in delta_tokens):
            return k
    for k, v in metrics.items():
        if is_stat_dict(v):
            return k
    return None


def read_result_json(experiments_root: Path, plan_id: str) -> dict | None:
    p = experiments_root / plan_id / "result.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


# ---- main entry point ------------------------------------------------------


def format_results_tables(thread: list[dict], experiments_root: Path) -> str:
    """Generate a markdown block of results tables for every ExperimentResult.

    Robust to multiple result.json schemas:
    - Canonical nested: metrics.proposed.<m> / metrics.baseline.<m>
    - Flat with naming convention: proposed_X / baseline_X paired up
    - Flat with explicit deltas: cost_savings_pp_vs_X, etc. — shown as-is

    Always emits:
      * A summary table (one row per experiment) — picks a "main metric"
      * Per-experiment detail blocks with: notes, pairwise table (when pairs
        detected), and a flat all-metrics table.
    """
    plans = {p["id"]: p for p in thread if p.get("type") == "ExperimentPlan"}
    results = [r for r in thread if r.get("type") == "ExperimentResult"]
    hyps = {h["id"]: h for h in thread if h.get("type") == "Hypothesis"}
    if not results:
        return ""

    summary_rows: list[str] = []
    detail_blocks: list[str] = []

    for res in results:
        plan_id = res.get("plan_id")
        plan = plans.get(plan_id, {})
        rj = read_result_json(experiments_root, plan_id) or {}
        metrics = rj.get("metrics") or {}
        if not metrics:
            artifact_m = res.get("metrics")
            if isinstance(artifact_m, str):
                try:
                    artifact_m = json.loads(artifact_m)
                except json.JSONDecodeError:
                    artifact_m = None
            if isinstance(artifact_m, dict):
                metrics = artifact_m
        if not isinstance(metrics, dict) or not metrics:
            continue

        # Detect schema: nested vs. flat
        nested = (
            isinstance(metrics.get("proposed"), dict)
            and isinstance(metrics.get("baseline"), dict)
            and any(is_stat_dict(v) for v in metrics.get("proposed", {}).values())
        )
        if nested:
            proposed = metrics["proposed"]
            baseline = metrics["baseline"]
            flat = {
                **{f"proposed_{k}": v for k, v in proposed.items()},
                **{f"baseline_{k}": v for k, v in baseline.items()},
            }
            pairs = [(k, f"proposed_{k}", f"baseline_{k}") for k in proposed if k in baseline]
        else:
            flat = {k: v for k, v in metrics.items() if is_stat_dict(v)}
            pairs = detect_proposed_baseline_pairs(flat)

        if not flat:
            continue

        # Linked Hypothesis
        hyp_id = next((p for p in (plan.get("parent_ids") or []) if p.startswith("HYP-")), None)
        hyp = hyps.get(hyp_id, {}) if hyp_id else {}
        pred_metric = hyp.get("prediction_metric", "") or ""
        pred_threshold = (
            hyp.get("prediction_threshold")
            or rj.get("hypothesis_threshold")
            or rj.get("hypothesis_threshold_pp")
            or rj.get("hypothesis_threshold_pct")
        )
        pred_direction = hyp.get("prediction_direction", "") or rj.get("threshold_direction", "")

        status = (res.get("status") or rj.get("status") or "?").lower()
        marker = {"pass": "**✓ pass**", "fail": "✗ fail", "crash": "⚠ crash"}.get(
            status, f"? {status}"
        )
        is_ablation = " *(ablation)*" if plan.get("is_ablation") else ""

        # Summary row
        sm = pick_summary_metric(flat, pred_metric)
        if sm:
            m = flat[sm]
            mean_str = fmt_num(m.get("mean"))
            stddev_str = fmt_num(m.get("stddev") or 0, 2)
            thr_str = ""
            if pred_threshold is not None:
                op = (
                    "≥"
                    if str(pred_direction).lower() in ("greater", "higher", "up", "+")
                    else (
                        "≤"
                        if str(pred_direction).lower() in ("less", "lower", "down", "-")
                        else "vs"
                    )
                )
                thr_str = f" (target {op}{fmt_num(pred_threshold)})"
            hyp_short = (hyp.get("summary", "") or "")[:50].replace("|", "\\|")
            summary_rows.append(
                f"| `{plan_id}`{is_ablation} | `{hyp_id or '—'}` {hyp_short} | "
                f"`{sm}` | {mean_str} ± {stddev_str}{thr_str} | {marker} |"
            )

        # Pairwise table
        pair_rows = []
        for base, p_key, b_key in pairs:
            p = flat.get(p_key, {})
            b = flat.get(b_key, {})
            if not (is_stat_dict(p) and is_stat_dict(b)):
                continue
            d = p["mean"] - b["mean"]
            n = p.get("n_seeds") or b.get("n_seeds") or "?"
            pair_rows.append(
                f"| `{base}` | {fmt_num(b['mean'])} ± {fmt_num(b.get('stddev', 0), 2)} | "
                f"{fmt_num(p['mean'])} ± {fmt_num(p.get('stddev', 0), 2)} | {d:+.4g} | {n} |"
            )

        # Flat all-metrics table (excluding pair members)
        flat_rows = []
        paired_keys = {pk for _, pk, _ in pairs} | {bk for _, _, bk in pairs}
        for k in sorted(flat.keys()):
            if k in paired_keys:
                continue
            m = flat[k]
            tag = " ←" if k == pred_metric else ""
            flat_rows.append(
                f"| `{k}`{tag} | {fmt_num(m.get('mean'))} ± {fmt_num(m.get('stddev', 0), 2)} | "
                f"{m.get('n_seeds', '?')} |"
            )

        notes = rj.get("notes") or rj.get("hypothesis_result") or ""

        # Block assembly
        parts = [
            f"#### `{plan_id}`{is_ablation} → "
            f"{(hyp.get('summary','')[:140] if hyp_id else '(no linked hypothesis)')}\n"
        ]
        if pred_metric or pred_threshold is not None:
            thr_part = (
                f" {pred_direction or ''} {fmt_num(pred_threshold)}".strip()
                if pred_threshold is not None
                else ""
            )
            parts.append(
                f"_Prediction: `{pred_metric or '?'}`"
                f"{(' ' + thr_part) if thr_part else ''} — {marker}_\n"
            )
        else:
            parts.append(f"_Status: {marker}_\n")
        if notes:
            parts.append(f"**Notes:** {notes}\n")
        if pair_rows:
            parts.append(
                "##### Proposed vs Baseline\n\n"
                "| Metric | Baseline | Proposed | Δ | Seeds |\n"
                "|--------|----------|----------|---|-------|\n" + "\n".join(pair_rows) + "\n"
            )
        if flat_rows:
            heading = "##### Other Metrics" if pair_rows else "##### Metrics"
            parts.append(
                f"{heading}\n\n"
                "| Metric | Mean ± StdDev | Seeds |\n"
                "|--------|---------------|-------|\n" + "\n".join(flat_rows) + "\n"
            )
        detail_blocks.append("\n".join(parts))

    if not summary_rows and not detail_blocks:
        return ""

    out = ["### Results Summary\n"]
    if summary_rows:
        out.append(
            "| Plan | Hypothesis | Main Metric | Result | Status |\n"
            "|------|------------|-------------|--------|--------|\n"
            + "\n".join(summary_rows)
            + "\n"
        )
    if detail_blocks:
        out.append("\n### Per-Experiment Detail\n\n" + "\n\n".join(detail_blocks))
    return "\n".join(out)
