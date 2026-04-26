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
  * cost ledger sum exceeds MAX_BUDGET_USD env var (default 10)

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


def append_cost(phase: str, skill: str, model: str, claude_json: dict):
    cl = cost_ledger()
    cl.parent.mkdir(parents=True, exist_ok=True)
    if not cl.exists():
        cl.write_text(
            "timestamp\tphase\tskill\tmodel\tinput_tokens\toutput_tokens\tusd\n"
        )
    usage = claude_json.get("usage", {}) or {}
    in_tok = usage.get("input_tokens", 0) or 0
    out_tok = usage.get("output_tokens", 0) or 0
    usd = claude_json.get("total_cost_usd", 0.0) or 0.0
    with cl.open("a") as f:
        f.write(
            f"{now_iso()}\t{phase}\t{skill}\t{model}\t{in_tok}\t{out_tok}\t{usd:.6f}\n"
        )


def cost_total_usd() -> float:
    cl = cost_ledger()
    if not cl.exists():
        return 0.0
    total = 0.0
    with cl.open() as f:
        next(f, None)
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 7:
                try:
                    total += float(parts[6])
                except ValueError:
                    pass
    return total


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
            f"call_claude exit={r.returncode} phase={phase} stderr={r.stderr[:400]}"
        )
    try:
        envelope = json.loads(r.stdout) if r.stdout.strip() else {}
    except json.JSONDecodeError:
        envelope = {"is_error": True, "result": r.stdout, "raw_stderr": r.stderr}
    append_cost(phase, skill, model, envelope)
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
    cap = float(os.environ.get("MAX_BUDGET_USD", "10"))
    spend = cost_total_usd()
    if spend >= cap:
        return f"cost {spend:.2f} >= budget {cap:.2f}"
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
    jobs = []
    for h in hyps[:5]:
        prompt = (
            f"Phase: survey\n"
            f"Invoke skill: literature-scout\n"
            f"Target: {h['id']}\n\n"
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
    jobs = []
    for h in survivors:
        prompt = (
            f"Phase: design\n"
            f"Invoke skill: experiment-designer (mode=primary)\n"
            f"Target: {h['id']}\n\n"
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
    return new_results


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
    for key, header in order:
        out.append(header)
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
    return [str(final_path)]


def next_phase_to_run(args) -> str | None:
    cp = latest_checkpoint()
    if cp is None:
        return "seed" if args.idea else None
    cur = cp.get("phase", "seed")
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
