#!/usr/bin/env python3
"""autolab orchestrator (project-aware).

Drives the 10-phase pipeline: seed -> expand -> survey -> gap-fill -> screen
-> design -> run -> critique -> write -> final, scoped to a single project
selected via the AUTOLAB_PROJECT env var.

The `start` and `resume` shell scripts set AUTOLAB_PROJECT before invoking
this script. Subprocesses (`claude -p`, tools/*.py, tools/*.sh) inherit it.

Stop conditions:
  * <project>/thread/checkpoints/final.json exists
  * STOP file at repo root

Usage:
    AUTOLAB_PROJECT=<id> tools/run_orchestrator.py --idea "..."   # fresh run
    AUTOLAB_PROJECT=<id> tools/run_orchestrator.py --resume       # continue
    AUTOLAB_PROJECT=<id> tools/run_orchestrator.py --resume --hypothesis "..."
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from _paths import (
    PROGRAM,
    REPO,
    STOP_FILE,
    TOOLS,
    checkpoints_dir,
    cost_ledger,
    drafts_dir,
    experiments_dir,
    get_project_id,
    init_project_dir,
    orchestrator_log,
    parking_lot,
    project_dir,
    thoughts_dir,
    thread_log,
)

PHASES = [
    "seed",
    "expand",
    "survey",
    "gap-fill",
    "screen",
    "design",
    "run",
    "critique",
    "write",
    "final",
]

# Phases re-run on retreat (everything from survey through critique).
RETREAT_PHASES = ["survey", "gap-fill", "screen", "design", "run", "critique"]

MAX_CYCLES = int(os.environ.get("AUTOLAB_MAX_CYCLES", "5"))
MAX_CRASH_RETRIES = int(os.environ.get("AUTOLAB_MAX_CRASH_RETRIES", "2"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_line(msg: str):
    p = orchestrator_log()
    p.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{now_iso()}] {msg}"
    with p.open("a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def read_thread() -> list[dict]:
    log = thread_log()
    if not log.exists():
        return []
    out = []
    with log.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def latest_checkpoint() -> dict | None:
    ckdir = checkpoints_dir()
    ckdir.mkdir(parents=True, exist_ok=True)
    files = sorted(ckdir.glob("*.json"))
    if not files:
        return None
    by_phase = {}
    for f in files:
        try:
            data = json.loads(f.read_text())
            by_phase[data.get("phase", f.stem)] = data
        except json.JSONDecodeError:
            continue
    for phase in reversed(PHASES):
        if phase in by_phase:
            return by_phase[phase]
    return None


def write_checkpoint(phase: str, completed_ids: list[str], next_action: str | None):
    ckdir = checkpoints_dir()
    ckdir.mkdir(parents=True, exist_ok=True)
    data = {
        "phase": phase,
        "completed_artifact_ids": completed_ids,
        "next_action": next_action,
        "completed_at": now_iso(),
    }
    (ckdir / f"{phase}.json").write_text(json.dumps(data, indent=2))


def _result_envelope(parsed) -> dict:
    """Normalize parsed `claude -p` stdout into a single result-envelope dict.

    `--output-format json` should return one dict, but some CLI versions emit
    a list of events (stream-json style). Drill in either way; never raise.
    """
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        for ev in reversed(parsed):
            if isinstance(ev, dict) and (
                ev.get("type") == "result"
                or "usage" in ev
                or "total_cost_usd" in ev
            ):
                return ev
        for ev in reversed(parsed):
            if isinstance(ev, dict):
                return ev
    return {}


def append_cost(phase: str, skill: str, model: str, claude_json):
    """Append a token-usage row to the ledger. USD is intentionally not tracked.

    Columns: timestamp, phase, skill, model, input_tokens (fresh, uncached),
    cache_creation_tokens, cache_read_tokens, output_tokens.
    """
    cl = cost_ledger()
    cl.parent.mkdir(parents=True, exist_ok=True)
    if not cl.exists():
        cl.write_text(
            "timestamp\tphase\tskill\tmodel\t"
            "input_tokens\tcache_creation_tokens\tcache_read_tokens\toutput_tokens\n"
        )
    env = _result_envelope(claude_json)
    usage = env.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    fresh_in = usage.get("input_tokens", 0) or 0
    cache_create = usage.get("cache_creation_input_tokens", 0) or 0
    cache_read = usage.get("cache_read_input_tokens", 0) or 0
    out_tok = usage.get("output_tokens", 0) or 0
    with cl.open("a") as f:
        f.write(
            f"{now_iso()}\t{phase}\t{skill}\t{model}\t"
            f"{fresh_in}\t{cache_create}\t{cache_read}\t{out_tok}\n"
        )


def project_paths_block() -> str:
    """Inject the active project's relative paths into every subagent prompt."""
    pid = get_project_id()
    base = f"projects/{pid}"
    return (
        f"\n## Active project\n"
        f"Project id: `{pid}`\n"
        f"Project root: `{base}/`\n"
        f"Thread index: `{base}/thread/INDEX.md`\n"
        f"Thoughts dir: `{base}/thoughts/`\n"
        f"Papers dir: `{base}/papers/`\n"
        f"Experiments dir: `{base}/experiments/`\n"
        f"Drafts dir: `{base}/drafts/`\n"
        f"Ideas/parking lot: `{base}/ideas/parking_lot.md`\n"
        f"All read/write paths in this phase resolve under this project root. "
        f"The tools (`tools/append_artifact.py`, `tools/refresh_indexes.py`, etc.) "
        f"already read AUTOLAB_PROJECT={pid} from the env; you do not need to pass it.\n"
    )


def call_claude(
    phase: str,
    skill: str,
    model: str,
    prompt: str,
    timeout_s: int = 1200,
) -> dict:
    """Spawn a headless `claude -p` call. Returns the parsed JSON envelope."""
    sys_prompt = PROGRAM.read_text() + "\n" + project_paths_block()
    cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "--model",
        model,
        "--output-format",
        "json",
        "--append-system-prompt",
        sys_prompt,
        "-p",
        prompt,
    ]
    log_line(f"call_claude phase={phase} skill={skill} model={model}")
    env = os.environ.copy()
    for k in (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ):
        env.pop(k, None)
    env["AUTOLAB_PROJECT"] = get_project_id()
    try:
        r = subprocess.run(
            cmd,
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log_line(f"call_claude TIMEOUT phase={phase} skill={skill}")
        return {"is_error": True, "error": "timeout", "result": ""}
    if r.returncode != 0:
        log_line(
            f"call_claude exit={r.returncode} phase={phase} skill={skill}\n"
            f"  stdout: {r.stdout[:2000] if r.stdout else '(empty)'}\n"
            f"  stderr: {r.stderr[:2000] if r.stderr else '(empty)'}"
        )
    try:
        parsed = json.loads(r.stdout) if r.stdout.strip() else {}
    except json.JSONDecodeError:
        parsed = {"is_error": True, "result": r.stdout, "raw_stderr": r.stderr}
    envelope = _result_envelope(parsed)
    # Debug: log the raw usage block so we can verify cache attribution.
    _u = envelope.get("usage") if isinstance(envelope, dict) else None
    if isinstance(_u, dict):
        log_line(
            f"call_claude usage phase={phase} skill={skill} "
            f"in={_u.get('input_tokens')} "
            f"cache_create={_u.get('cache_creation_input_tokens')} "
            f"cache_read={_u.get('cache_read_input_tokens')} "
            f"out={_u.get('output_tokens')}"
        )
    append_cost(phase, skill, model, envelope)
    if r.returncode != 0 or envelope.get("is_error"):
        raise SystemExit(
            f"claude failed in phase={phase} skill={skill} rc={r.returncode} "
            f"envelope_keys={list(envelope.keys())}; see logs/orchestrator.log for full output"
        )
    return envelope


def parallel_calls(jobs: list[dict]) -> list[dict]:
    results: list[dict] = [None] * len(jobs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(jobs))) as ex:
        futures = {
            ex.submit(
                call_claude,
                j["phase"],
                j["skill"],
                j["model"],
                j["prompt"],
                j.get("timeout_s", 1200),
            ): i
            for i, j in enumerate(jobs)
        }
        for fut in concurrent.futures.as_completed(futures):
            i = futures[fut]
            results[i] = fut.result()
    return results


def append_via_tool(args: list[str], stdin: str | None = None) -> str:
    proc = subprocess.run(
        [sys.executable, str(TOOLS / "append_artifact.py")] + args,
        cwd=REPO,
        env={**os.environ, "AUTOLAB_PROJECT": get_project_id()},
        capture_output=True,
        text=True,
        input=stdin,
        check=True,
    )
    return proc.stdout.strip().splitlines()[-1]


def write_idea_artifact(seed: str) -> str:
    aid = append_via_tool(
        [
            "--type",
            "Idea",
            "--author",
            "orchestrator",
            "--summary",
            seed,
            "--field",
            f"seed={json.dumps(seed)}",
            "--field",
            "framing=" + json.dumps("seed idea provided via CLI"),
            "--field",
            "open_questions=[]",
        ]
    )
    log_line(f"seed: emitted {aid}")
    return aid


def write_seed_hypothesis(text: str) -> str:
    """Emit a Hypothesis directly, used by `resume --hypothesis "..."`."""
    thread = read_thread()
    ideas = [r for r in thread if r.get("type") == "Idea"]
    parent = ideas[-1]["id"] if ideas else ""
    aid = append_via_tool(
        [
            "--type",
            "Hypothesis",
            "--author",
            "user",
            "--parent",
            parent,
            "--summary",
            text,
            "--field",
            f"claim={json.dumps(text)}",
            "--field",
            'prediction_metric=""',
            "--field",
            "prediction_threshold=0",
            "--field",
            'prediction_direction="user-supplied"',
            "--field",
            f"prerequisites={json.dumps([parent] if parent else [])}",
        ]
    )
    log_line(f"resume: seeded user Hypothesis {aid}")
    return aid


def refresh_indexes():
    subprocess.run(
        [sys.executable, str(TOOLS / "refresh_indexes.py")],
        cwd=REPO,
        env={**os.environ, "AUTOLAB_PROJECT": get_project_id()},
        check=False,
    )


def by_type(thread: list[dict], t: str) -> list[dict]:
    return [r for r in thread if r.get("type") == t]


def stop_conditions_met() -> str | None:
    if (checkpoints_dir() / "final.json").exists():
        return "final checkpoint exists"
    if STOP_FILE.exists():
        return "STOP file present"
    return None


def phase_seed(idea_text: str) -> list[str]:
    if not idea_text:
        raise SystemExit("seed phase requires --idea")
    aid = write_idea_artifact(idea_text)
    refresh_indexes()
    return [aid]


def phase_expand() -> list[str]:
    thread = read_thread()
    ideas = by_type(thread, "Idea")
    if not ideas:
        raise SystemExit("expand: no Idea artifact found; run seed first")
    target = ideas[-1]["id"]
    prompt = (
        f"Phase: expand\n"
        f"Invoke skill: idea-expander (mode=expand)\n"
        f"Target: {target}\n\n"
        f"Read thread/INDEX.md and thoughts/{target}.md (under the active project root). "
        f"Per the idea-expander skill, emit 3-5 Hypothesis rows. "
        f"At least one MUST be a cross-domain transplant. "
        f"Each MUST include prediction_metric, prediction_threshold, prediction_direction. "
        f"Use tools/append_artifact.py for emission. End with the stdout contract."
    )
    call_claude("expand", "idea-expander", "sonnet", prompt)
    refresh_indexes()
    return [r["id"] for r in by_type(read_thread(), "Hypothesis")]


def phase_survey() -> list[str]:
    thread = read_thread()
    hyps = by_type(thread, "Hypothesis")
    if not hyps:
        raise SystemExit("survey: no Hypothesis artifacts to survey")
    cycle_ctx = cycle_context_block(read_cycle_state())
    jobs = []
    for h in hyps[:5]:
        prompt = (
            f"Phase: survey\n"
            f"Invoke skill: literature-scout\n"
            f"Target: {h['id']}\n\n"
            f"{cycle_ctx}"
            f"Read thread/INDEX.md and thoughts/{h['id']}.md (under the active project root). "
            f"Per the literature-scout skill, fetch 3-7 papers and emit LitFinding rows. "
            f"Use tools/fetch_paper.py for caching, then tools/append_artifact.py for emission. "
            f"End with the stdout contract."
        )
        jobs.append(
            {
                "phase": "survey",
                "skill": "literature-scout",
                "model": "sonnet",
                "prompt": prompt,
                "timeout_s": 1800,
            }
        )
    parallel_calls(jobs)
    refresh_indexes()
    return [r["id"] for r in by_type(read_thread(), "LitFinding")]


def phase_gap_fill() -> list[str]:
    thread = read_thread()
    ideas = by_type(thread, "Idea")
    if not ideas:
        raise SystemExit("gap-fill: no Idea")
    target = ideas[-1]["id"]
    prompt = (
        f"Phase: gap-fill\n"
        f"Invoke skill: idea-expander (mode=gap-fill)\n"
        f"Target: {target}\n\n"
        f"Read thread/INDEX.md, thoughts/{target}.md, and every thoughts/LIT-*.md. "
        f"Per the idea-expander skill (gap-fill mode), identify the question conspicuously absent "
        f"from the LitFinding set and emit 1-2 Hypothesis rows. End with the stdout contract."
    )
    call_claude("gap-fill", "idea-expander", "sonnet", prompt)
    refresh_indexes()
    return [
        r["id"]
        for r in by_type(read_thread(), "Hypothesis")
        if r.get("author") == "idea-expander"
    ]


def phase_screen() -> list[str]:
    thread = read_thread()
    hyps = by_type(thread, "Hypothesis")
    if not hyps:
        raise SystemExit("screen: no Hypothesis")

    boredom_jobs = []
    for h in hyps:
        prompt = (
            f"Phase: screen-boredom\n"
            f"Invoke skill: critic (mode=boredom)\n"
            f"Target: {h['id']}\n\n"
            f"Read thoughts/{h['id']}.md and any LitFindings linked via parent_ids. "
            f"Per the critic skill (boredom mode), emit one Critique. "
            f"End with the stdout contract."
        )
        boredom_jobs.append(
            {
                "phase": "screen-boredom",
                "skill": "critic",
                "model": "haiku",
                "prompt": prompt,
            }
        )
    parallel_calls(boredom_jobs)

    nov_prompt = (
        f"Phase: screen-novelty\n"
        f"Invoke skill: novelty-checker\n\n"
        f"Read thread/INDEX.md. For each Hypothesis row, run tools/verify_citation.py "
        f"against each linked LitFinding's arxiv_id. Emit Citation rows for each pair "
        f"and high-severity Critiques for collisions (score >= 0.85). "
        f"End with the stdout contract."
    )
    call_claude("screen-novelty", "novelty-checker", "haiku", nov_prompt)

    refresh_indexes()
    park_failed_hypotheses()
    return [r["id"] for r in read_thread() if r.get("type") == "Critique"]


def park_failed_hypotheses():
    thread = read_thread()
    hyps = {r["id"]: r for r in by_type(thread, "Hypothesis")}
    parked: list[str] = []
    for crit in by_type(thread, "Critique"):
        if crit.get("severity") != "high":
            continue
        if crit.get("mode") not in ("boredom", "validity"):
            continue
        target = crit.get("target_id")
        if target in hyps and target not in parked:
            parked.append(target)
    if not parked:
        return
    pl = parking_lot()
    pl.parent.mkdir(parents=True, exist_ok=True)
    with pl.open("a") as f:
        f.write(f"\n## Parked at {now_iso()}\n\n")
        for hid in parked:
            h = hyps[hid]
            f.write(f"- `{hid}` ({h.get('author','?')}): {h.get('summary','')}\n")
    log_line(f"parked {len(parked)} hypotheses: {parked}")


def surviving_hypotheses() -> list[dict]:
    thread = read_thread()
    hyps = by_type(thread, "Hypothesis")
    parked = set()
    for crit in by_type(thread, "Critique"):
        if (
            crit.get("severity") == "high"
            and crit.get("mode") in ("boredom", "validity")
            and crit.get("target_id", "").startswith("HYP-")
        ):
            parked.add(crit["target_id"])
    return [h for h in hyps if h["id"] not in parked]


def phase_design(benchmark: str | None) -> list[str]:
    survivors = surviving_hypotheses()
    if not survivors:
        log_line("design: no surviving hypotheses; nothing to design")
        return []
    bench_note = f" Benchmark hint: {benchmark}." if benchmark else ""
    cycle_ctx = cycle_context_block(read_cycle_state())
    jobs = []
    for h in survivors:
        prompt = (
            f"Phase: design\n"
            f"Invoke skill: experiment-designer (mode=primary)\n"
            f"Target: {h['id']}\n\n"
            f"{cycle_ctx}"
            f"Read thoughts/{h['id']}.md. Per the experiment-designer skill, "
            f"emit one ExperimentPlan with seeds (>=3) and baseline_spec.{bench_note} "
            f"End with the stdout contract."
        )
        jobs.append(
            {
                "phase": "design",
                "skill": "experiment-designer",
                "model": "opus",
                "prompt": prompt,
                "timeout_s": 1200,
            }
        )
    parallel_calls(jobs)
    refresh_indexes()
    return [r["id"] for r in by_type(read_thread(), "ExperimentPlan")]


def phase_run() -> list[str]:
    queue: list[str] = [
        p["id"]
        for p in by_type(read_thread(), "ExperimentPlan")
        if not p.get("is_ablation", False)
    ]
    new_results: list[str] = []
    seen_plans: set[str] = set()
    while queue:
        pid = queue.pop(0)
        if pid in seen_plans:
            continue
        seen_plans.add(pid)
        prompt = (
            f"Phase: run\n"
            f"Invoke skill: experiment-runner\n"
            f"Target: {pid}\n\n"
            f"Read thoughts/{pid}.md. Per the experiment-runner skill, "
            f"materialize code/run.py under experiments/{pid}/, run sanity gate, "
            f"then run the multi-seed sweep. Emit one ExperimentResult. "
            f"End with the stdout contract."
        )
        call_claude("run", "experiment-runner", "sonnet", prompt, timeout_s=2400)
        refresh_indexes()
        results_for_plan = [
            r
            for r in by_type(read_thread(), "ExperimentResult")
            if r.get("plan_id") == pid
        ]
        if not results_for_plan:
            continue
        latest = results_for_plan[-1]
        new_results.append(latest["id"])
        if latest.get("status") != "pass":
            continue
        plan = next(
            (p for p in by_type(read_thread(), "ExperimentPlan") if p["id"] == pid),
            None,
        )
        if plan and plan.get("is_ablation"):
            continue
        ablation_prompt = (
            f"Phase: design-ablation\n"
            f"Invoke skill: experiment-designer (mode=ablation)\n"
            f"Target: {pid}\n\n"
            f"Read thoughts/{pid}.md and thoughts/{latest['id']}.md. "
            f"Per the experiment-designer skill (ablation mode), emit one "
            f"ExperimentPlan with is_ablation=true that removes the proposed mechanism. "
            f"End with the stdout contract."
        )
        call_claude(
            "design-ablation",
            "experiment-designer",
            "opus",
            ablation_prompt,
            timeout_s=1200,
        )
        refresh_indexes()
        for p in by_type(read_thread(), "ExperimentPlan"):
            if (
                p.get("is_ablation")
                and pid in (p.get("parent_ids") or [])
                and p["id"] not in seen_plans
            ):
                queue.append(p["id"])
    # Orchestrator-level crash retries: any plan whose latest result is `crash`
    # gets re-run with a debug-fix prompt, up to MAX_CRASH_RETRIES times each.
    for _ in range(MAX_CRASH_RETRIES + 1):
        if not crash_retry_pass():
            break
    # Recompute the new_results list to include any retried results.
    final_results: list[str] = []
    seen_plan_results: set[str] = set()
    for r in by_type(read_thread(), "ExperimentResult"):
        if r["id"] in new_results or r.get("plan_id") in {pid for pid in seen_plans}:
            if r["id"] not in seen_plan_results:
                final_results.append(r["id"])
                seen_plan_results.add(r["id"])
    return final_results or new_results


def phase_critique() -> list[str]:
    results = by_type(read_thread(), "ExperimentResult")
    if not results:
        return []
    targets = ",".join(r["id"] for r in results)
    prompt = (
        f"Phase: critique\n"
        f"Invoke skill: critic (mode=validity)\n"
        f"Targets: {targets}\n\n"
        f"For each ExperimentResult above, read its body and the linked plan. "
        f"Per the critic skill (validity mode), emit one Critique per RES id "
        f"covering threats to validity, baseline parity, statistical concerns. "
        f"End with the stdout contract."
    )
    call_claude("critique", "critic", "opus", prompt, timeout_s=1800)
    refresh_indexes()
    return [
        r["id"]
        for r in by_type(read_thread(), "Critique")
        if r.get("mode") == "validity" and r.get("author") == "critic"
    ]


def phase_write() -> list[str]:
    sections = [
        "outline",
        "abstract",
        "introduction",
        "related-work",
        "method",
        "experiments",
        "discussion",
    ]
    thread = read_thread()
    cite_pool = [r["id"] for r in by_type(thread, "Citation") if r.get("verified")]
    relevant = ",".join(
        [r["id"] for r in by_type(thread, "Idea")]
        + [r["id"] for r in by_type(thread, "Hypothesis")]
        + [r["id"] for r in by_type(thread, "ExperimentPlan")]
        + [r["id"] for r in by_type(thread, "ExperimentResult")]
        + [r["id"] for r in by_type(thread, "Critique") if r.get("mode") == "validity"]
    )
    new_ids: list[str] = []
    for sec in sections:
        prompt = (
            f"Phase: write\n"
            f"Invoke skill: paper-writer\n"
            f"section={sec}\n"
            f"version=1\n"
            f"cite_pool={','.join(cite_pool) or '(none)'}\n"
            f"relevant_artifacts={relevant}\n\n"
            f"Per the paper-writer skill, produce one DraftSection. "
            f"Write the section body to thoughts/<DRAFT-id>.md and append to drafts/citations.bib. "
            f"End with the stdout contract."
        )
        call_claude("write", "paper-writer", "opus", prompt, timeout_s=1800)
        refresh_indexes()
        latest = [
            r
            for r in by_type(read_thread(), "DraftSection")
            if r.get("section") == sec
        ]
        if latest:
            new_ids.append(latest[-1]["id"])
    return new_ids


def _fmt_num(v, sig: int = 4) -> str:
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


def _read_result_json(plan_id: str) -> dict | None:
    p = experiments_dir() / plan_id / "result.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _format_results_tables() -> str:
    """Generate a markdown block of results tables comparing proposed vs baseline
    for every ExperimentResult that has a corresponding result.json on disk.

    Output: a summary table (one row per experiment) + per-experiment detail tables
    (one row per metric, with mean ± stddev for both conditions and Δ).
    """
    thread = read_thread()
    plans = {p["id"]: p for p in by_type(thread, "ExperimentPlan")}
    results = by_type(thread, "ExperimentResult")
    hyps = {h["id"]: h for h in by_type(thread, "Hypothesis")}
    if not results:
        return ""

    summary_rows: list[str] = []
    detail_blocks: list[str] = []

    for res in results:
        plan_id = res.get("plan_id")
        plan = plans.get(plan_id, {})
        rj = _read_result_json(plan_id)
        if not rj:
            continue
        metrics = rj.get("metrics", {})
        proposed = metrics.get("proposed", {}) or {}
        baseline = metrics.get("baseline", {}) or {}
        if not proposed and not baseline:
            continue

        # Linked Hypothesis (first HYP- parent of the plan)
        hyp_id = next(
            (p for p in (plan.get("parent_ids") or []) if p.startswith("HYP-")),
            None,
        )
        hyp = hyps.get(hyp_id, {}) if hyp_id else {}
        pred_metric = hyp.get("prediction_metric", "") or ""
        pred_threshold = hyp.get("prediction_threshold", "")
        pred_direction = hyp.get("prediction_direction", "")

        status = (res.get("status") or "?").lower()
        marker = {"pass": "**✓ pass**", "fail": "✗ fail", "crash": "⚠ crash"}.get(status, f"? {status}")
        is_ablation = " *(ablation)*" if plan.get("is_ablation") else ""

        # Summary row
        if pred_metric and pred_metric in proposed:
            p_mean = proposed[pred_metric].get("mean")
            b_mean = baseline.get(pred_metric, {}).get("mean")
            delta = (p_mean - b_mean) if (p_mean is not None and b_mean is not None) else None
            hyp_short = (hyp.get("summary", "") or "")[:50].replace("|", "\\|")
            summary_rows.append(
                f"| `{plan_id}`{is_ablation} | `{hyp_id or '—'}` {hyp_short} | "
                f"`{pred_metric}` | {_fmt_num(b_mean)} | {_fmt_num(p_mean)} | "
                f"{(_fmt_num(delta) if delta is None else f'{delta:+.4g}')} | {marker} |"
            )

        # Detail block
        all_metrics = sorted(set(proposed.keys()) | set(baseline.keys()))
        rows = []
        for m in all_metrics:
            b = baseline.get(m, {}) or {}
            p = proposed.get(m, {}) or {}
            b_str = (
                f"{_fmt_num(b.get('mean'))} ± {_fmt_num(b.get('stddev'), 2)}"
                if b else "—"
            )
            p_str = (
                f"{_fmt_num(p.get('mean'))} ± {_fmt_num(p.get('stddev'), 2)}"
                if p else "—"
            )
            n = p.get("n_seeds") or b.get("n_seeds") or 0
            d = None
            if b and p and b.get("mean") is not None and p.get("mean") is not None:
                d = p["mean"] - b["mean"]
            d_str = f"{d:+.4g}" if d is not None else "—"
            tag = " ←" if m == pred_metric else ""
            rows.append(f"| `{m}`{tag} | {b_str} | {p_str} | {d_str} | {n} |")

        threshold_note = ""
        if pred_metric:
            threshold_note = (
                f"_Hypothesis prediction: `{pred_metric}` "
                f"{pred_direction} threshold `{pred_threshold}` — {marker}_\n\n"
            )

        detail_blocks.append(
            f"#### `{plan_id}`{is_ablation} → {(hyp.get('summary','')[:120] if hyp_id else '(no linked hypothesis)')}\n\n"
            f"{threshold_note}"
            f"| Metric | Baseline (mean ± std) | Proposed (mean ± std) | Δ | Seeds |\n"
            f"|--------|----------------------|----------------------|---|-------|\n"
            + "\n".join(rows)
        )

    if not summary_rows and not detail_blocks:
        return ""

    out = ["### Results Summary\n"]
    if summary_rows:
        out.append(
            "| Plan | Hypothesis | Predicted Metric | Baseline | Proposed | Δ | Status |\n"
            "|------|------------|------------------|----------|----------|---|--------|\n"
            + "\n".join(summary_rows)
            + "\n"
        )
    else:
        out.append("_(no predicted-metric rows available)_\n")
    if detail_blocks:
        out.append("\n### Per-Experiment Detail\n\n" + "\n\n".join(detail_blocks) + "\n")
    return "\n".join(out)


def phase_final() -> list[str]:
    drafts = drafts_dir()
    drafts.mkdir(parents=True, exist_ok=True)
    order = [
        ("abstract", "## Abstract"),
        ("introduction", "## 1. Introduction"),
        ("related-work", "## 2. Related Work"),
        ("method", "## 3. Method"),
        ("experiments", "## 4. Experiments"),
        ("discussion", "## 5. Discussion"),
    ]
    sections = {r["section"]: r for r in by_type(read_thread(), "DraftSection")}
    title = "Autolab Generated Paper"
    ideas = by_type(read_thread(), "Idea")
    if ideas:
        title = ideas[-1].get("summary", title)[:120]
    out = [f"# {title}", ""]
    results_tables = _format_results_tables()
    for key, header in order:
        out.append(header)
        # Inject auto-generated results tables at the top of the Experiments
        # section so the reader can skim outcomes before the prose.
        if key == "experiments" and results_tables:
            out.append(results_tables)
        sec = sections.get(key)
        if not sec:
            out.append("_(missing)_\n")
            continue
        body_path = project_dir() / sec.get("body_path", "")
        if body_path.exists():
            text = body_path.read_text()
            parts = text.split("---\n", 2)
            out.append(parts[-1].strip() if len(parts) >= 3 else text.strip())
        out.append("")
    final_path = drafts / "paper-vFINAL.md"
    final_path.write_text("\n".join(out) + "\n")
    log_line(f"final: wrote {final_path}")
    pdf_path = drafts / "paper-vFINAL.pdf"
    bib_path = drafts / "citations.bib"
    err = render_pdf(final_path, bib_path, pdf_path)
    out_paths = [str(final_path)]
    if err:
        log_line(f"final: PDF skipped — {err}")
    else:
        log_line(f"final: wrote {pdf_path}")
        out_paths.append(str(pdf_path))
    return out_paths


def render_pdf(md_path: Path, bib_path: Path, out_path: Path) -> str | None:
    """Render `md_path` to `out_path` via pandoc. Returns None on success,
    or a human-readable error string. Never raises."""
    if not md_path.exists():
        return f"source markdown missing: {md_path}"
    if not shutil.which("pandoc"):
        return (
            "pandoc not installed. Install with `brew install pandoc basictex` "
            "(macOS) or `apt install pandoc texlive-xetex` (Linux). "
            "The .md is the canonical artifact; PDF is a convenience render."
        )
    cmd = [
        "pandoc",
        str(md_path),
        "-o", str(out_path),
        "--citeproc",
        "--standalone",
        "-V", "geometry:margin=1in",
        "-V", "fontsize=11pt",
        "-V", "linkcolor:blue",
        "-V", "colorlinks=true",
    ]
    if bib_path.exists():
        cmd += ["--bibliography", str(bib_path)]
    # Prefer xelatex if present (better unicode); else let pandoc auto-pick.
    if shutil.which("xelatex"):
        cmd += ["--pdf-engine", "xelatex"]
    elif shutil.which("pdflatex"):
        cmd += ["--pdf-engine", "pdflatex"]
    elif shutil.which("wkhtmltopdf"):
        cmd += ["--pdf-engine", "wkhtmltopdf"]
    elif shutil.which("weasyprint"):
        cmd += ["--pdf-engine", "weasyprint"]
    else:
        return (
            "no PDF engine found. Install one: `brew install basictex` (xelatex), "
            "`brew install --cask wkhtmltopdf`, or `pip install weasyprint`."
        )
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return "pandoc timed out (>180s)"
    except FileNotFoundError as e:
        return f"pandoc invocation failed: {e}"
    if r.returncode != 0:
        return f"pandoc rc={r.returncode}: {(r.stderr or r.stdout).strip()[:400]}"
    return None


def cycle_state_path() -> Path:
    return checkpoints_dir().parent / "cycles.json"


def read_cycle_state() -> dict:
    """{ current: int, history: [{cycle, ended_at, failed_plan_ids, failed_hyp_ids, summary}], crash_retries: {plan_id: int} }"""
    p = cycle_state_path()
    if not p.exists():
        return {"current": 1, "history": [], "crash_retries": {}}
    try:
        s = json.loads(p.read_text())
        s.setdefault("current", 1)
        s.setdefault("history", [])
        s.setdefault("crash_retries", {})
        return s
    except json.JSONDecodeError:
        return {"current": 1, "history": [], "crash_retries": {}}


def write_cycle_state(state: dict):
    p = cycle_state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2))


def _wipe_checkpoints_from(phase_name: str):
    """Remove checkpoints for `phase_name` and every later phase, forcing rerun."""
    if phase_name not in PHASES:
        return
    start_idx = PHASES.index(phase_name)
    ckdir = checkpoints_dir()
    for ph in PHASES[start_idx:]:
        f = ckdir / f"{ph}.json"
        if f.exists():
            f.unlink()


def _last_critique_completed_at() -> str | None:
    """Timestamp the latest 'critique' checkpoint was written, used to scope
    'current cycle' artifacts vs. those from prior cycles."""
    ck = checkpoints_dir() / "critique.json"
    if not ck.exists():
        return None
    try:
        return json.loads(ck.read_text()).get("completed_at")
    except json.JSONDecodeError:
        return None


def _experiment_results_after(boundary_iso: str | None) -> list[dict]:
    thread = read_thread()
    results = by_type(thread, "ExperimentResult")
    if not boundary_iso:
        return results
    return [r for r in results if (r.get("created_at") or r.get("ts") or "") > boundary_iso]


def cycle_retreat_check() -> str | None:
    """Decide whether to retreat after the just-completed `critique` phase.

    Returns the phase name to retreat to ("survey") if conditions met, else None.
    """
    state = read_cycle_state()
    cycle = state["current"]
    if MAX_CYCLES > 0 and cycle >= MAX_CYCLES:
        log_line(f"retreat: at MAX_CYCLES={MAX_CYCLES}, advancing to write")
        return None
    # Look at results emitted since the previous cycle's retreat (or all results
    # if this is cycle 1). The boundary is the previous cycle's ended_at marker.
    prev_boundary = state["history"][-1]["ended_at"] if state["history"] else None
    results = _experiment_results_after(prev_boundary)
    # Ignore ablation results — we care about whether the *primary* hypothesis test passed.
    primary = [r for r in results if not r.get("is_ablation", False)]
    if not primary:
        log_line("retreat: no primary ExperimentResults found; not retreating")
        return None
    has_pass = any(r.get("status") == "pass" for r in primary)
    if has_pass:
        log_line(f"retreat: cycle {cycle} has pass result(s); advancing to write")
        return None
    # No positive result. Park the failed hypotheses so subagents don't reuse them,
    # record the cycle, and retreat to survey.
    failed_plan_ids = [r.get("plan_id") for r in primary if r.get("plan_id")]
    failed_hyp_ids = []
    plans_by_id = {p["id"]: p for p in by_type(read_thread(), "ExperimentPlan")}
    for pid in failed_plan_ids:
        plan = plans_by_id.get(pid, {})
        for parent in plan.get("parent_ids") or []:
            if parent.startswith("HYP-") and parent not in failed_hyp_ids:
                failed_hyp_ids.append(parent)
    park_hypotheses(failed_hyp_ids, reason=f"cycle {cycle}: experiments did not produce a positive result")
    state["history"].append({
        "cycle": cycle,
        "ended_at": now_iso(),
        "failed_plan_ids": failed_plan_ids,
        "failed_hyp_ids": failed_hyp_ids,
        "summary": f"{len(primary)} primary experiment(s), 0 pass",
    })
    state["current"] = cycle + 1
    write_cycle_state(state)
    _wipe_checkpoints_from("survey")
    log_line(
        f"retreat: cycle {cycle} → cycle {cycle+1}; "
        f"parked {len(failed_hyp_ids)} HYPs ({failed_hyp_ids}); "
        f"wiped checkpoints from survey onward"
    )
    return "survey"


def park_hypotheses(hyp_ids: list[str], reason: str):
    if not hyp_ids:
        return
    pl = parking_lot()
    pl.parent.mkdir(parents=True, exist_ok=True)
    thread = read_thread()
    by_id = {h["id"]: h for h in by_type(thread, "Hypothesis")}
    with pl.open("a") as f:
        f.write(f"\n## Parked at {now_iso()} — {reason}\n\n")
        for hid in hyp_ids:
            h = by_id.get(hid, {})
            f.write(f"- `{hid}` ({h.get('author','?')}): {h.get('summary','')}\n")


def crash_retry_pass() -> int:
    """After phase_run, retry experiment-runner for plans whose only results crashed.

    Returns the number of retries performed this pass. Bounded per-plan by
    MAX_CRASH_RETRIES (separate from the 2 retries the runner does internally).
    """
    state = read_cycle_state()
    retries_done = 0
    thread = read_thread()
    plans = [p for p in by_type(thread, "ExperimentPlan") if not p.get("is_ablation")]
    for plan in plans:
        pid = plan["id"]
        results_for = [r for r in by_type(thread, "ExperimentResult") if r.get("plan_id") == pid]
        if not results_for:
            continue
        latest = results_for[-1]
        if latest.get("status") != "crash":
            continue
        used = state["crash_retries"].get(pid, 0)
        if used >= MAX_CRASH_RETRIES:
            log_line(f"crash-retry: {pid} exhausted ({used}/{MAX_CRASH_RETRIES}), giving up")
            continue
        state["crash_retries"][pid] = used + 1
        write_cycle_state(state)
        log_line(f"crash-retry: re-running {pid} (orchestrator attempt {used+1}/{MAX_CRASH_RETRIES})")
        prompt = (
            f"Phase: run-debug-retry\n"
            f"Invoke skill: experiment-runner\n"
            f"Target: {pid}\n\n"
            f"PRIOR ATTEMPT CRASHED. Read thoughts/{pid}.md, the latest "
            f"experiments/{pid}/runs/*.log, and any failure-analysis Critiques. "
            f"Per the experiment-runner skill, diagnose the crash, edit "
            f"experiments/{pid}/code/run.py to address the root cause "
            f"(common: hyperparam out of range, dtype mismatch, OOM, missing import, "
            f"shape error). Re-run with sanity gate then full sweep. Emit a fresh "
            f"ExperimentResult. End with the stdout contract."
        )
        call_claude("run-debug-retry", "experiment-runner", "sonnet", prompt, timeout_s=2400)
        refresh_indexes()
        retries_done += 1
    return retries_done


def cycle_context_block(state: dict) -> str:
    """Prompt prefix injected into survey/design phases when cycle > 1."""
    if state["current"] <= 1 or not state["history"]:
        return ""
    last = state["history"][-1]
    failed_hyps = last.get("failed_hyp_ids", [])
    failed_plans = last.get("failed_plan_ids", [])
    return (
        f"\n## RETREAT CONTEXT (cycle {state['current']} of up to {MAX_CYCLES})\n"
        f"This is iteration {state['current']}. Previous cycle(s) did NOT yield a positive result.\n"
        f"Parked failed Hypotheses (do not re-propose these): {failed_hyps}\n"
        f"Failed ExperimentPlans: {failed_plans}\n"
        f"Read each parked HYP's body and any linked ExperimentResult/Critique to "
        f"understand WHY it failed (wrong mechanism? bad metric? confounded baseline?). "
        f"Propose materially different angles — not minor variations of the same idea.\n"
    )


def next_phase_to_run(args) -> str | None:
    cp = latest_checkpoint()
    if cp is None:
        return "seed" if args.idea else None
    cur = cp.get("phase", "seed")
    # Retreat hook: after critique, decide whether to loop back to survey.
    if cur == "critique":
        retreat = cycle_retreat_check()
        if retreat:
            return retreat
    try:
        i = PHASES.index(cur)
    except ValueError:
        return None
    if i + 1 >= len(PHASES):
        return None
    return PHASES[i + 1]


def run_phase(phase: str, args) -> list[str]:
    log_line(f"=== begin phase: {phase} ===")
    if phase == "seed":
        ids = phase_seed(args.idea)
    elif phase == "expand":
        ids = phase_expand()
    elif phase == "survey":
        ids = phase_survey()
    elif phase == "gap-fill":
        ids = phase_gap_fill()
    elif phase == "screen":
        ids = phase_screen()
    elif phase == "design":
        ids = phase_design(args.benchmark)
    elif phase == "run":
        ids = phase_run()
    elif phase == "critique":
        ids = phase_critique()
    elif phase == "write":
        ids = phase_write()
    elif phase == "final":
        ids = phase_final()
    else:
        raise SystemExit(f"unknown phase: {phase}")
    write_checkpoint(
        phase,
        ids,
        None if phase == "final" else PHASES[PHASES.index(phase) + 1],
    )
    log_line(f"=== end phase: {phase} ids={ids} ===")
    return ids


def consume_parking() -> str | None:
    pl = parking_lot()
    if not pl.exists():
        return None
    lines = pl.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("- `HYP-"):
            try:
                summary = line.split(":", 1)[1].strip()
            except IndexError:
                continue
            del lines[i]
            pl.write_text("\n".join(lines))
            return summary
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idea", help="Seed research idea (one line)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--resume-from-bank", action="store_true")
    ap.add_argument("--hypothesis", help="Seed an additional Hypothesis directly (resume)")
    ap.add_argument("--benchmark", help="Bias designer toward a tracked benchmark")
    ap.add_argument(
        "--single-step",
        action="store_true",
        help="Run only the next phase, then exit",
    )
    args = ap.parse_args()

    pid = get_project_id()
    init_project_dir(pid)

    if args.resume_from_bank and not args.idea:
        idea = consume_parking()
        if not idea:
            log_line("resume-from-bank: parking_lot.md has no parked HYP entries")
            sys.exit(0)
        args.idea = idea

    if args.hypothesis:
        write_seed_hypothesis(args.hypothesis)
        refresh_indexes()

    if not args.idea and not args.resume and not args.hypothesis:
        cp = latest_checkpoint()
        if cp is None:
            ap.error("--idea or --resume required (no prior checkpoint)")

    while True:
        stop_reason = stop_conditions_met()
        if stop_reason:
            log_line(f"stop: {stop_reason}")
            return
        phase = next_phase_to_run(args)
        if phase is None:
            log_line("no more phases")
            return
        try:
            run_phase(phase, args)
        except Exception as e:
            log_line(f"phase {phase} ERROR: {e}")
            raise
        if args.single_step:
            return


if __name__ == "__main__":
    main()
