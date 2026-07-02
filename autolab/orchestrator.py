#!/usr/bin/env python3
"""autolab orchestrator (project-aware).

Drives the phase pipeline: seed -> expand -> survey -> gap-fill -> screen
-> thought-experiment -> design -> run -> critique -> write -> final -> review,
scoped to a single project selected via the AUTOLAB_PROJECT env var.

The `start` and `resume` shell scripts set AUTOLAB_PROJECT before invoking
this script. Subprocesses (`claude -p`, tools/*.py, tools/*.sh) inherit it.

Stop conditions:
  * <project>/thread/checkpoints/<terminal-phase>.json exists
    (terminal phase is the last entry in PHASES; currently `review`)
  * STOP file at repo root

Usage:
    AUTOLAB_PROJECT=<id> python -m autolab.orchestrator --idea "..."   # fresh run
    AUTOLAB_PROJECT=<id> python -m autolab.orchestrator --resume       # continue
    AUTOLAB_PROJECT=<id> python -m autolab.orchestrator --resume --hypothesis "..."
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from autolab.paths import (
    PROGRAM,
    REPO,
    STOP_FILE,
    checkpoints_dir,
    cost_ledger,
    drafts_dir,
    experiments_dir,
    get_project_id,
    history_log,
    init_project_dir,
    orchestrator_log,
    parking_lot,
    project_dir,
    thread_log,
)
from autolab.results_tables import format_results_tables as _fmt_tables_impl

PHASES = [
    "seed",
    "expand",
    "survey",
    "gap-fill",
    "screen",
    "thought-experiment",
    "design",
    "run",
    "critique",
    "write",
    "final",
    "review",
]

# Phases re-run on retreat (everything from survey through critique).
RETREAT_PHASES = [
    "survey",
    "gap-fill",
    "screen",
    "thought-experiment",
    "design",
    "run",
    "critique",
]

# Phases a committee reviewer may request as a `target_phase` for a major
# revision. Anything outside this set is treated as a minor revision.
VALID_REVIEW_LOOPBACK_PHASES = {"survey", "design", "run", "critique", "write", "final"}

MAX_CYCLES = int(os.environ.get("AUTOLAB_MAX_CYCLES", "5"))
MAX_CRASH_RETRIES = int(os.environ.get("AUTOLAB_MAX_CRASH_RETRIES", "2"))
MAX_IDEA_CYCLES = int(os.environ.get("AUTOLAB_MAX_IDEA_CYCLES", "3"))
MAX_REVIEW_CYCLES = int(os.environ.get("AUTOLAB_MAX_REVIEW_CYCLES", "2"))
MAX_RUN_DESIGN_CYCLES = int(os.environ.get("AUTOLAB_MAX_RUN_DESIGN_CYCLES", "2"))
MIN_WILD_HYPOTHESES = int(os.environ.get("AUTOLAB_MIN_WILD_HYPOTHESES", "2"))

REVIEWER_PERSONAS = [
    {
        "id": "methodologist",
        "focus": (
            "Experimental design, statistical validity, baseline parity, "
            "seed counts, ablation coverage, reproducibility envelope. "
            "Cross-check claims in the paper against validity-mode "
            "Critique artifacts; flag any claim the artifacts do not "
            "support. Penalize single-seed RL results."
        ),
    },
    {
        "id": "domain-expert",
        "focus": (
            "Novelty, contribution, and positioning vs. cited literature. "
            "Are the claims supported by the experiments? Is the related "
            "work coverage adequate? Are obvious neighbors missing from "
            "cite_pool? For negative-results work, evaluate whether the "
            "refutation is genuinely informative or merely a null."
        ),
    },
    {
        "id": "clarity-reviewer",
        "focus": (
            "Writing, structure, and story. Is the introduction's "
            "contributions list 1-for-1 with the experiments headline "
            "table? Are sections complete and self-consistent? Would a "
            "NeurIPS reviewer reading only Abstract + §1 + the main "
            "table walk away with the right takeaway?"
        ),
    },
]

WILDNESS_CRITERIA = """## WILDNESS BAR (read carefully)

Every Hypothesis you emit MUST satisfy at least ONE of the following tickets.
State which ticket(s) it satisfies in the body.

  (W1) Cross-domain transplant from a NON-ML field. Acceptable source fields:
       neuroscience, biology, physics, control theory, evolutionary theory,
       economics, linguistics, signal processing, statistics-beyond-ML,
       chemistry, statistical mechanics. RL→supervised, vision→NLP,
       optimization→architecture are TOO CLOSE — they do NOT count.
  (W2) Explicitly contradicts a textbook claim or widely-held assumption.
       State the textbook claim verbatim, then state your counter-claim.
  (W3) Measures something nobody has measured for this setup at meaningful
       scale. State why the measurement was missing (cost? unfashionable?
       no obvious method?).
  (W4) Regime swap — what changes when scale, data quality, modality, or
       compute is 100× or 0.01× the standard? The hypothesis must commit to
       a numeric prediction in the new regime.

REJECT-YOURSELF examples (do NOT emit these):
  - "Test if X works on Y" (too obvious; produces a measurement, not insight)
  - "Try variant of method M" (incrementalism)
  - "Replicate paper P with smaller model" (replication, not novelty)
  - "Combine A and B" (without a *mechanistic* reason the combination matters)
  - Any hypothesis whose result a sharp PhD student would predict in 30 seconds

A hypothesis that fails the wildness bar will be parked at screen. The
orchestrator will retreat and ask you to try again — wilder.
"""


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


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
                ev.get("type") == "result" or "usage" in ev or "total_cost_usd" in ev
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
        f"The tools (`python -m autolab.append_artifact`, "
        f"`python -m autolab.refresh_indexes`, etc.) already read "
        f"AUTOLAB_PROJECT={pid} from the env; you do not need to pass it.\n"
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
        [sys.executable, "-m", "autolab.append_artifact", *args],
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
        [sys.executable, "-m", "autolab.refresh_indexes"],
        cwd=REPO,
        env={**os.environ, "AUTOLAB_PROJECT": get_project_id()},
        check=False,
    )


def by_type(thread: list[dict], t: str) -> list[dict]:
    return [r for r in thread if r.get("type") == t]


def stop_conditions_met() -> str | None:
    # The orchestrator is done only when the *terminal* phase has emitted
    # its checkpoint. PHASES[-1] is the source of truth — historically
    # this was `final`, but `review` is now the terminal phase. Hardcoding
    # "final.json" caused runs to exit before the committee ever ran.
    terminal = PHASES[-1]
    if (checkpoints_dir() / f"{terminal}.json").exists():
        return f"{terminal} checkpoint exists"
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
    history_ctx = history_block()
    prompt = (
        f"Phase: expand\n"
        f"Invoke skill: idea-expander (mode=expand)\n"
        f"Target: {target}\n\n"
        f"{history_ctx}"
        f"{WILDNESS_CRITERIA}\n"
        f"Read thread/INDEX.md and thoughts/{target}.md (under the active project root). "
        f"Per the idea-expander skill, emit 3-5 Hypothesis rows that satisfy the "
        f"WILDNESS BAR above. At least one MUST be a W1 cross-domain transplant from "
        f"a non-ML field. Each MUST include prediction_metric, prediction_threshold, "
        f"prediction_direction, and a body that explicitly names the wildness ticket(s) "
        f"it satisfies. Use `python -m autolab.append_artifact` for emission. End with the stdout contract."
    )
    call_claude("expand", "idea-expander", "fable", prompt)
    refresh_indexes()
    return [r["id"] for r in by_type(read_thread(), "Hypothesis")]


def phase_survey() -> list[str]:
    thread = read_thread()
    hyps = by_type(thread, "Hypothesis")
    if not hyps:
        raise SystemExit("survey: no Hypothesis artifacts to survey")
    history_ctx = history_block()
    jobs = []
    for h in hyps[:5]:
        prompt = (
            f"Phase: survey\n"
            f"Invoke skill: literature-scout\n"
            f"Target: {h['id']}\n\n"
            f"{history_ctx}"
            f"Read thread/INDEX.md and thoughts/{h['id']}.md (under the active project root). "
            f"Per the literature-scout skill, fetch 3-7 papers and emit LitFinding rows. "
            f"Use `python -m autolab.fetch_paper` for caching, then "
            f"`python -m autolab.append_artifact` for emission. "
            f"End with the stdout contract."
        )
        jobs.append(
            {
                "phase": "survey",
                "skill": "literature-scout",
                "model": "fable",
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
    history_ctx = history_block()
    prompt = (
        f"Phase: gap-fill\n"
        f"Invoke skill: idea-expander (mode=gap-fill)\n"
        f"Target: {target}\n\n"
        f"{history_ctx}"
        f"{WILDNESS_CRITERIA}\n"
        f"Read thread/INDEX.md, thoughts/{target}.md, and every thoughts/LIT-*.md. "
        f"Per the idea-expander skill (gap-fill mode), identify the question conspicuously absent "
        f"from the LitFinding set and emit 1-2 Hypothesis rows that satisfy the WILDNESS BAR. "
        f"End with the stdout contract."
    )
    call_claude("gap-fill", "idea-expander", "fable", prompt)
    refresh_indexes()
    return [
        r["id"] for r in by_type(read_thread(), "Hypothesis") if r.get("author") == "idea-expander"
    ]


def phase_screen() -> list[str]:
    thread = read_thread()
    hyps = by_type(thread, "Hypothesis")
    if not hyps:
        raise SystemExit("screen: no Hypothesis")
    history_ctx = history_block()

    boredom_jobs = []
    for h in hyps:
        prompt = (
            f"Phase: screen-boredom\n"
            f"Invoke skill: critic (mode=boredom)\n"
            f"Target: {h['id']}\n\n"
            f"{history_ctx}"
            f"Read thoughts/{h['id']}.md and any LitFindings linked via parent_ids. "
            f"Per the critic skill (boredom mode), emit one Critique.\n"
            f"\n## Wildness bar (apply STRICTLY in addition to trivial/known/dead-end)\n"
            f"Mark severity=high if ANY of the following hold:\n"
            f"  - The hypothesis would be unsurprising to a sharp PhD student in the field "
            f"(rate it 'dead-end' with concern 'low novelty: outcome predictable').\n"
            f"  - It is an incremental tweak of a standard method without a mechanistic "
            f"reason the tweak matters.\n"
            f"  - It claims to satisfy Wildness Ticket W1 (cross-domain) but the source "
            f"field is just an adjacent ML subfield (RL, vision, NLP, optimization). "
            f"Real W1 sources: neuroscience, biology, physics, economics, linguistics, "
            f"control theory, evolutionary theory.\n"
            f"  - It is a replication, ablation framed as novelty, or 'combine A and B' "
            f"without mechanistic justification.\n"
            f"Calibration target: at most ~1-in-3 hypotheses should survive. Use the "
            f"strongest argument you can construct against the idea, then judge severity.\n"
            f"End with the stdout contract."
        )
        boredom_jobs.append(
            {
                "phase": "screen-boredom",
                "skill": "critic",
                "model": "fable",
                "prompt": prompt,
            }
        )
    parallel_calls(boredom_jobs)

    nov_prompt = (
        "Phase: screen-novelty\n"
        "Invoke skill: novelty-checker\n\n"
        f"{history_ctx}"
        "Read thread/INDEX.md. For each Hypothesis row, run "
        "`python -m autolab.verify_citation` against each linked LitFinding's "
        "arxiv_id. Emit Citation rows for each pair and high-severity Critiques "
        "for collisions (score >= 0.85). End with the stdout contract."
    )
    call_claude("screen-novelty", "novelty-checker", "fable", nov_prompt)

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


_FRAMEWORK_HINT_CACHE: str | None = None


def _framework_hint() -> str:
    """Return a definitive string the experiment-designer can trust about
    framework availability on this machine. Cached after first probe."""
    global _FRAMEWORK_HINT_CACHE
    if _FRAMEWORK_HINT_CACHE is not None:
        return _FRAMEWORK_HINT_CACHE
    try:
        import mlx.core as mx  # noqa: F401

        device = str(mx.default_device())
        _FRAMEWORK_HINT_CACHE = (
            "## Framework availability (REQUIRED)\n"
            f"`mlx` is INSTALLED on this machine. Default device: {device}. "
            'Set `framework="mlx"` in your ExperimentPlan and write the '
            "code_skeleton using `import mlx.core as mx`, `import mlx.nn as nn`, "
            "`import mlx.optimizers as optim`. Seed via `mx.random.seed(seed)`. "
            "Use `torch` ONLY if you need an op MLX genuinely lacks (rare for MLP, "
            "transformer, CNN, RNN, attention, AdamW, gradient clipping, etc.).\n\n"
        )
    except ImportError:
        _FRAMEWORK_HINT_CACHE = (
            "## Framework availability\n"
            '`mlx` is NOT installed on this machine — use `framework="torch"` '
            "with CPU device. (Note: this run is missing the preferred backend; "
            "performance will be much slower than MLX on Apple Silicon.)\n\n"
        )
    return _FRAMEWORK_HINT_CACHE


def phase_thought_experiment() -> list[str]:
    """Roll out a toy-problem thought experiment per surviving Hypothesis.

    Pure reasoning, no compute: for each hypothesis that cleared `screen`, the
    thought-experimenter designs a deliberate toy problem isolating the
    mechanism, simulates it mentally against the null, names the failure modes,
    and renders a verdict (promising / inconclusive / refuted). Scalability is
    contemplated only AFTER the toy rollout. The verdict gates `design`.
    """
    survivors = surviving_hypotheses()
    if not survivors:
        log_line("thought-experiment: no surviving hypotheses; nothing to roll out")
        return []
    history_ctx = history_block()
    jobs = []
    for h in survivors:
        prompt = (
            f"Phase: thought-experiment\n"
            f"Invoke skill: thought-experimenter\n"
            f"Target: {h['id']}\n\n"
            f"{history_ctx}"
            f"Read thoughts/{h['id']}.md and any LitFindings linked via parent_ids. "
            f"Per the thought-experimenter skill, design ONE deliberate toy problem that "
            f"isolates the hypothesized mechanism, roll the experiment forward in your head "
            f"(hypothesis trajectory vs. null), name the failure modes, and render a verdict "
            f"(promising | inconclusive | refuted). Only AFTER the rollout, sketch the single "
            f"concrete step from the toy problem toward an informative (non-toy) experiment. "
            f"Do NOT contemplate scale before the toy rollout is done, and do NOT default to a "
            f"stock benchmark unless it is genuinely the minimal probe of the claim. "
            f"Emit one ThoughtExperiment via `python -m autolab.append_artifact`. "
            f"End with the stdout contract."
        )
        jobs.append(
            {
                "phase": "thought-experiment",
                "skill": "thought-experimenter",
                "model": "fable",
                "prompt": prompt,
                "timeout_s": 1200,
            }
        )
    parallel_calls(jobs)
    refresh_indexes()
    return [r["id"] for r in by_type(read_thread(), "ThoughtExperiment")]


def thought_experiments_by_hyp() -> dict[str, dict]:
    """Map each Hypothesis id to its latest ThoughtExperiment artifact (if any)."""
    out: dict[str, dict] = {}
    for te in by_type(read_thread(), "ThoughtExperiment"):
        hid = te.get("hypothesis_id") or next(
            (p for p in (te.get("parent_ids") or []) if str(p).startswith("HYP-")),
            None,
        )
        if hid:
            out[hid] = te  # chronological iteration → latest wins
    return out


def park_refuted_hypotheses(hyps: list[dict], tes: dict[str, dict]):
    """Append thought-experiment-refuted hypotheses to the parking lot with the
    refutation reasoning attached, mirroring screen's boredom parking."""
    if not hyps:
        return
    pl = parking_lot()
    pl.parent.mkdir(parents=True, exist_ok=True)
    with pl.open("a") as f:
        f.write(f"\n## Parked at {now_iso()} (thought experiment refuted)\n\n")
        for h in hyps:
            te = tes.get(h["id"], {})
            f.write(f"- `{h['id']}` ({h.get('author', '?')}): {h.get('summary', '')}\n")
            toy = te.get("toy_problem")
            if toy:
                f.write(f"    - toy problem: {toy}\n")
            reason = te.get("predicted_outcome") or te.get("summary")
            if reason:
                f.write(f"    - refuted: {reason}\n")
    log_line(
        f"parked {len(hyps)} thought-experiment-refuted hypotheses: " f"{[h['id'] for h in hyps]}"
    )


def phase_design(benchmark: str | None) -> list[str]:
    survivors = surviving_hypotheses()
    if not survivors:
        log_line("design: no surviving hypotheses; nothing to design")
        return []
    # Gate on the thought-experiment verdict: hypotheses whose toy-problem
    # rollout refuted the mechanism are parked, not designed. Safety net: if
    # EVERY survivor was refuted, proceed with all of them rather than ending
    # the run empty — pessimism shouldn't be able to nuke the whole pipeline.
    tes = thought_experiments_by_hyp()
    refuted = [h for h in survivors if tes.get(h["id"], {}).get("verdict") == "refuted"]
    cleared = [h for h in survivors if tes.get(h["id"], {}).get("verdict") != "refuted"]
    if not cleared:
        log_line(
            "design: every surviving hypothesis was refuted by its thought "
            "experiment; proceeding with all survivors rather than ending empty"
        )
        cleared, refuted = survivors, []
    park_refuted_hypotheses(refuted, tes)
    bench_note = f" Benchmark hint: {benchmark}." if benchmark else ""
    history_ctx = history_block()
    fw_hint = _framework_hint()
    jobs = []
    for h in cleared:
        te = tes.get(h["id"])
        if te:
            te_block = (
                f"## Thought experiment for {h['id']} "
                f"(verdict: {te.get('verdict', '?')})\n"
                f"Toy problem: {te.get('toy_problem', '')}\n"
                f"Predicted toy-scale outcome: {te.get('predicted_outcome', '')}\n"
                f"Mechanism: {te.get('mechanism', '')}\n"
                f"Path to an informative experiment: {te.get('scalability_note', '')}\n"
                f"Read thoughts/{te['id']}.md for the full rollout. Build the "
                f"ExperimentPlan as the FIRST informative (non-toy) step beyond this "
                f"toy problem — ground it in the deciding comparison the thought "
                f"experiment identified, and do NOT default to MNIST or a generic "
                f"benchmark.\n\n"
            )
        else:
            te_block = ""
        prompt = (
            f"Phase: design\n"
            f"Invoke skill: experiment-designer (mode=primary)\n"
            f"Target: {h['id']}\n\n"
            f"{fw_hint}"
            f"{te_block}"
            f"{history_ctx}"
            f"Read thoughts/{h['id']}.md. Per the experiment-designer skill, "
            f"emit one ExperimentPlan with seeds (>=3) and baseline_spec.{bench_note} "
            f"End with the stdout contract."
        )
        jobs.append(
            {
                "phase": "design",
                "skill": "experiment-designer",
                "model": "fable",
                "prompt": prompt,
                "timeout_s": 1200,
            }
        )
    parallel_calls(jobs)
    refresh_indexes()
    return [r["id"] for r in by_type(read_thread(), "ExperimentPlan")]


def phase_run() -> list[str]:
    queue: list[str] = [
        p["id"] for p in by_type(read_thread(), "ExperimentPlan") if not p.get("is_ablation", False)
    ]
    new_results: list[str] = []
    seen_plans: set[str] = set()
    history_ctx = history_block()
    while queue:
        pid = queue.pop(0)
        if pid in seen_plans:
            continue
        seen_plans.add(pid)
        prompt = (
            f"Phase: run\n"
            f"Invoke skill: experiment-runner\n"
            f"Target: {pid}\n\n"
            f"{history_ctx}"
            f"Read thoughts/{pid}.md. Per the experiment-runner skill, "
            f"materialize code/run.py under experiments/{pid}/, run sanity gate, "
            f"then run the multi-seed sweep. Emit one ExperimentResult. "
            f"End with the stdout contract."
        )
        call_claude("run", "experiment-runner", "fable", prompt, timeout_s=2400)
        refresh_indexes()
        results_for_plan = [
            r for r in by_type(read_thread(), "ExperimentResult") if r.get("plan_id") == pid
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
            f"{_framework_hint()}"
            f"Read thoughts/{pid}.md and thoughts/{latest['id']}.md. "
            f"Per the experiment-designer skill (ablation mode), emit one "
            f"ExperimentPlan with is_ablation=true that removes the proposed mechanism. "
            f"End with the stdout contract."
        )
        call_claude(
            "design-ablation",
            "experiment-designer",
            "fable",
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
    history_ctx = history_block()
    prompt = (
        f"Phase: critique\n"
        f"Invoke skill: critic (mode=validity)\n"
        f"Targets: {targets}\n\n"
        f"{history_ctx}"
        f"For each ExperimentResult above, read its body and the linked plan. "
        f"Per the critic skill (validity mode), emit one Critique per RES id "
        f"covering threats to validity, baseline parity, statistical concerns. "
        f"End with the stdout contract."
    )
    call_claude("critique", "critic", "fable", prompt, timeout_s=1800)
    refresh_indexes()
    return [
        r["id"]
        for r in by_type(read_thread(), "Critique")
        if r.get("mode") == "validity" and r.get("author") == "critic"
    ]


def phase_write() -> list[str]:
    # Section order matches the NeurIPS structural standard documented in
    # skills/paper-writer/SKILL.md. Outline first (committing the contributions
    # list); then the front-matter (abstract, intro, related); then the
    # foundational sections (background, data-models); then method and
    # experiments; then the closing material (discussion, conclusion, impact,
    # reproducibility).
    sections = [
        "outline",
        "abstract",
        "introduction",
        "related-work",
        "background",
        "data-models",
        "method",
        "experiments",
        "discussion",
        "conclusion",
        "broader-impact",
        "reproducibility",
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
    # Pre-render the deterministic results tables once. The paper-writer is
    # instructed to paste them verbatim into the experiments section, and to
    # use them as a numerical reference for abstract/discussion. This guarantees
    # the prose is anchored to the same numbers as result.json on disk.
    results_tables = _format_results_tables()
    section_brief = _neurips_section_brief()
    history_ctx = history_block()
    new_ids: list[str] = []
    for sec in sections:
        prompt_parts = [
            "Phase: write",
            "Invoke skill: paper-writer",
            f"section={sec}",
            "version=1",
            f"cite_pool={','.join(cite_pool) or '(none)'}",
            f"relevant_artifacts={relevant}",
            "",
            history_ctx,
            "## Target structure (NeurIPS standard)",
            "",
            "The assembled paper must satisfy a NeurIPS-style structure: Title and "
            "Abstract; Introduction (with falsifiable contributions list and a "
            "Figure 1 teaser); Related Work (themed, each cluster ending with "
            "an explicit positioning sentence); Background and Preliminaries; "
            "Data and Models (full architecture and dataset spec, with "
            "consistency check); Method (formal problem statement, pseudocode, "
            "design-choice rationale, complexity); Experiments (setup, headline "
            "table/plot, ablations matching the contributions list 1-for-1, "
            "analysis, robustness with seeds and error bars); Discussion / "
            "Limitations (specific threats to validity, not boilerplate); "
            "Conclusion (one paragraph, no new claims); Broader Impact "
            "(concrete, not boilerplate); Reproducibility Statement; "
            "References; Appendix. The contributions bullets in the "
            "Introduction and the headline table in Experiments must tell the "
            "same story. Full per-section guidance is in "
            "skills/paper-writer/SKILL.md — read it before writing.",
            "",
            f"### This invocation: section={sec}",
            section_brief.get(sec, ""),
            "",
        ]
        if results_tables and sec == "experiments":
            prompt_parts.extend(
                [
                    "## Pre-rendered results tables (deterministic — paste VERBATIM)",
                    "",
                    "The orchestrator has rendered the canonical results tables from each "
                    "experiments/<EXP-id>/result.json. Paste the entire block below "
                    "VERBATIM into your experiments section body, then write your prose "
                    "AROUND it — sanity-gate notes, qualitative analysis, ablation discussion, "
                    "threats to validity. Do NOT retype the numbers in prose form. "
                    "Do NOT modify, summarize, or reformat the tables. Place the block at the "
                    "start of your section (before the prose) so readers can skim outcomes first.",
                    "",
                    "===== BEGIN PRE-RENDERED TABLES (paste verbatim) =====",
                    results_tables,
                    "===== END PRE-RENDERED TABLES =====",
                    "",
                ]
            )
        elif results_tables and sec in ("abstract", "discussion"):
            prompt_parts.extend(
                [
                    "## Reference data (use these numbers — do NOT paste verbatim)",
                    "",
                    "Below are the canonical results tables for accurate numerical reference. "
                    "When stating headline results in prose, use these exact numbers. The full "
                    "tables will appear in the Experiments section; you do not need to "
                    "reproduce them here.",
                    "",
                    results_tables,
                    "",
                ]
            )
        prompt_parts.append(
            "Per the paper-writer skill, produce one DraftSection. "
            "Write the section body to thoughts/<DRAFT-id>.md and append to drafts/citations.bib. "
            "\n\n**CRITICAL — Conference-ready language:** This paper is being submitted to a "
            "peer-reviewed conference. NEVER use internal artifact IDs (HYP-NNN, EXP-NNN, "
            "CRIT-NNN, LIT-NNN, RES-NNN, etc.) anywhere in the paper text. NEVER use "
            "pipeline jargon like 'decisively refuted', 'downgraded to preliminary status', "
            "'parked', 'wildness bar', 'retreat cycle'. Use standard academic language "
            "throughout. The paper must be indistinguishable from one written by hand for "
            "conference submission.\n\n"
            "End with the stdout contract."
        )
        prompt = "\n".join(prompt_parts)
        call_claude("write", "paper-writer", "fable", prompt, timeout_s=1800)
        refresh_indexes()
        latest = [r for r in by_type(read_thread(), "DraftSection") if r.get("section") == sec]
        if latest:
            new_ids.append(latest[-1]["id"])
    return new_ids


def _format_results_tables() -> str:
    return _fmt_tables_impl(read_thread(), experiments_dir())


def _neurips_section_brief() -> dict[str, str]:
    """One-paragraph NeurIPS-quality brief per section, injected into the
    paper-writer prompt to reinforce the standard at the call site. Full
    guidance lives in skills/paper-writer/SKILL.md."""
    return {
        "outline": (
            "4–7 bullets covering claim, method, evidence, contribution. "
            "No prose. The bullets you commit here become the contributions "
            "list in the introduction. Frame each bullet as a step in the "
            "narrative: question → approach → finding."
        ),
        "abstract": (
            "150–250 words. Tell a mini-story: problem → gap → approach → "
            "2–3 headline numbers (use exact values from the reference "
            "tables) → takeaway. Open with a sentence that makes the reader "
            "care *before* jumping to the solution. Commit to specific "
            "claims, not vague gestures. For negative-results work, lead "
            "with the refutation and quantify the falsified prediction."
        ),
        "introduction": (
            "~1 page. Hook the reader with *why this problem matters* — a "
            "concrete consequence, not a platitude. Brief survey of what's "
            "been tried and why it falls short (build tension). One-paragraph "
            "approach sketch giving intuition before details. Explicit "
            "contributions bullet list of *falsifiable claims*. The intro is "
            "a promise: 'here's the journey we'll take you on.' Mention a "
            "Figure 1 teaser even if not yet rendered."
        ),
        "related-work": (
            "Group cited papers by theme. For each cluster, tell a "
            "micro-story: what did this line try, what did they achieve, "
            "where does it leave us wanting? End each paragraph with an "
            "explicit positioning sentence. Bare citation lists without "
            "narrative are a red flag."
        ),
        "background": (
            "Notation, problem setup, formal definitions, prior results we "
            "build on. Motivate each definition — explain why the reader "
            "needs it for what follows. Self-contained for a reader fluent "
            "in the area; do not re-derive textbook material. May be folded "
            "into method if notation is standard."
        ),
        "data-models": (
            "Full data spec (sources, sizes, licenses, dates, mixture "
            "weights, preprocessing pipeline in order, splits, "
            "decontamination, summary statistics) and full model spec ($L$, "
            "$d_{\\text{model}}$, $d_{\\text{ff}}$, heads, head dim, KV "
            "heads, vocab, max seq len, position encoding, norm, "
            "activation, parameter count table, tokenizer, training "
            "recipe, compute footprint, checkpoint plans). Justify "
            "non-default choices. Run a consistency check: every component "
            "must reappear in method; every dataset must reappear in "
            "training/eval."
        ),
        "method": (
            "Start with the core insight (1–2 sentences a student could "
            "repeat back). Then: formal problem statement with locked "
            "notation, algorithm/architecture with pseudocode or diagram, "
            "theoretical analysis where applicable, design choices with "
            "rationale (why this and not the obvious alternative?), "
            "complexity analysis. The reader should understand the method's "
            "spirit before its letter."
        ),
        "experiments": (
            "Paste the pre-rendered tables verbatim at the top. Then write "
            "prose as a sequence of questions and answers: 'Does the "
            "mechanism help?' (main results), 'Which component does the "
            "work?' (ablations), 'Does it hold under stress?' (robustness). "
            "Frame each experiment as testing a specific claim. Ablations "
            "match contributions 1-for-1. Error bars or seed counts on "
            "every number. Interpret results — don't just report them."
        ),
        "discussion": (
            "Step back and reflect honestly. Why does it work (or not)? "
            "What surprised us? Specific threats to validity identified "
            "during the critique phase (distributions not tested, scales "
            "not reached, baselines not run). Frame limitations as open "
            "questions, not apologies. For negative results, name what "
            "would constitute positive evidence."
        ),
        "conclusion": (
            "One paragraph (≤ 150 words). Restate the contribution and "
            "point at future work. No new claims."
        ),
        "broader-impact": (
            "Concrete on dual-use, misuse vectors, and downstream effects "
            "specific to the contribution, not boilerplate. For pure "
            "methods papers, argue the impact-mediation chain rather than "
            "asserting 'limited risk.'"
        ),
        "reproducibility": (
            "Concrete pointers: code path, data path, per-experiment "
            "hyperparameter tables, pretrain caches, run logs, "
            "statistical-analysis scripts, pre-registration commit hash. "
            "Note non-determinism caveats explicitly."
        ),
    }


def phase_final() -> list[str]:
    drafts = drafts_dir()
    drafts.mkdir(parents=True, exist_ok=True)
    # NeurIPS-style assembly order. Headers must match what the paper-writer
    # skill (skills/paper-writer/SKILL.md) is asked to fill in.
    order = [
        ("abstract", "## Abstract"),
        ("introduction", "## 1. Introduction"),
        ("related-work", "## 2. Related Work"),
        ("background", "## 3. Background and Preliminaries"),
        ("data-models", "## 4. Data and Models"),
        ("method", "## 5. Method"),
        ("experiments", "## 6. Experiments"),
        ("discussion", "## 7. Discussion and Limitations"),
        ("conclusion", "## 8. Conclusion"),
        ("broader-impact", "## 9. Broader Impact Statement"),
        ("reproducibility", "## 10. Reproducibility Statement"),
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
        sec = sections.get(key)
        body_text = ""
        if sec:
            body_path = project_dir() / sec.get("body_path", "")
            if body_path.exists():
                text = body_path.read_text()
                parts = text.split("---\n", 2)
                body_text = parts[-1].strip() if len(parts) >= 3 else text.strip()
        # Safety net: if paper-writer was supposed to paste the tables into the
        # experiments section but didn't, inject them at assembly time so the
        # final paper is never missing them.
        if key == "experiments" and results_tables and "### Results Summary" not in body_text:
            log_line(
                "final: experiments section body lacks tables; " "injecting auto-rendered fallback"
            )
            out.append(results_tables)
        if body_text:
            out.append(body_text)
        else:
            out.append("_(missing)_\n")
        out.append("")
    final_path = drafts / "paper-vFINAL.md"
    final_path.write_text("\n".join(out) + "\n")
    log_line(f"final: wrote initial assembly to {final_path}")
    _run_polish_pass(final_path)
    return [str(final_path)]


def _run_polish_pass(paper_path: Path) -> None:
    """Re-read the assembled paper and run a clarity + completeness pass.

    Section-by-section writes occasionally leave gaps: a DraftSection may
    be missing (rendered `_(missing)_` by the assembly above), a body may
    be sparse, or two sections may contradict each other on numbers. The
    polish pass reads the full paper plus all artifacts and edits the
    file in place via the `paper-polisher` skill.

    Failures degrade gracefully: if the claude call errors out, we restore
    the pre-polish version from the backup so the user still has the
    assembled paper.

    Set `AUTOLAB_SKIP_POLISH=1` to disable.
    """
    if os.environ.get("AUTOLAB_SKIP_POLISH"):
        log_line("final: polish pass skipped (AUTOLAB_SKIP_POLISH set)")
        return
    if not paper_path.exists():
        log_line(f"final: polish skipped, {paper_path.name} missing")
        return

    backup_path = paper_path.with_name(paper_path.stem + ".pre-polish.md")
    backup_path.write_text(paper_path.read_text())
    log_line(f"final: backed up pre-polish version to {backup_path.name}")

    thread = read_thread()
    cite_pool = [r["id"] for r in by_type(thread, "Citation") if r.get("verified")]
    relevant = ",".join(
        [r["id"] for r in by_type(thread, "Idea")]
        + [r["id"] for r in by_type(thread, "Hypothesis")]
        + [r["id"] for r in by_type(thread, "ExperimentPlan")]
        + [r["id"] for r in by_type(thread, "ExperimentResult")]
        + [r["id"] for r in by_type(thread, "Critique") if r.get("mode") == "validity"]
    )
    results_tables = _format_results_tables()
    history_ctx = history_block()

    prompt_parts = [
        "Phase: polish",
        "Invoke skill: paper-polisher",
        f"paper_path={paper_path.relative_to(REPO)}",
        f"backup_path={backup_path.relative_to(REPO)}",
        f"cite_pool={','.join(cite_pool) or '(none)'}",
        f"relevant_artifacts={relevant}",
        "",
        history_ctx,
        "## Reference data (numerical anchor — do NOT alter the numbers)",
        "",
        "Below are the canonical results tables rendered from each "
        "experiments/<EXP-id>/result.json. Any numerical claim in the "
        "polished paper must agree with these exactly.",
        "",
        results_tables or "(no experiments yet — leave results-bearing prose untouched)",
        "",
        "## Goals for this pass",
        "",
        "1. **Completeness.** Find every '_(missing)_' placeholder and any "
        "section with fewer than ~3 sentences; replace with a complete body "
        "grounded in the artifacts and tables above. Use the NeurIPS "
        "structural standard in skills/paper-writer/SKILL.md as your rubric.",
        "2. **Clarity.** Tighten convoluted prose without changing claims. "
        "Remove duplicated phrasing across sections.",
        "3. **Consistency.** The introduction's contributions bullet list "
        "and the experiments headline table must tell the same story "
        "1-for-1. For negative-results work, lead with the falsified "
        "prediction; do not soften 'fail' into 'promising trend'.",
        "4. **Fidelity.** Cite only ids in cite_pool. Do not fabricate "
        "experiments, datasets, or numbers. Do not add or remove section "
        "headings. Preserve the title.",
        "5. **Scrub internal identifiers.** Search for and remove ALL "
        "internal artifact IDs (HYP-NNN, EXP-NNN, CRIT-NNN, LIT-NNN, "
        "RES-NNN, REV-NNN, DRAFT-NNN — any UPPERCASE-DIGITS pattern). "
        "Replace with descriptive phrases. Also remove pipeline jargon "
        "('decisively refuted', 'downgraded to preliminary status', "
        "'parked', 'wildness bar', 'retreat cycle', 'loopback'). Use "
        "standard academic language. This paper is being submitted to a "
        "peer-reviewed conference.",
        "",
        f"Edit {paper_path.relative_to(REPO)} in place. End with the stdout contract.",
    ]
    prompt = "\n".join(prompt_parts)

    try:
        call_claude("polish", "paper-polisher", "fable", prompt, timeout_s=1800)
        log_line(f"final: polish pass complete; final paper at {paper_path}")
    except SystemExit as e:
        # Polish is best-effort. If it fails, restore the pre-polish
        # version so the user still has the assembled paper.
        log_line(f"final: polish pass failed ({e}); restoring pre-polish version")
        paper_path.write_text(backup_path.read_text())


def phase_review() -> list[str]:
    """Run a 3-reviewer committee against the current paper-vFINAL.md.

    Each persona produces ONE Review artifact in parallel via the
    `committee-reviewer` skill. The orchestrator's loopback decision is
    made later in `review_loopback_check()` based on the aggregated
    recommendations.

    Set AUTOLAB_SKIP_REVIEW=1 to skip the committee entirely.
    """
    if os.environ.get("AUTOLAB_SKIP_REVIEW"):
        log_line("review: skipped (AUTOLAB_SKIP_REVIEW set)")
        return []

    paper = drafts_dir() / "paper-vFINAL.md"
    if not paper.exists():
        log_line("review: paper-vFINAL.md missing; skipping committee")
        return []

    state = read_cycle_state()
    rcycle = state.get("review_cycle", 1)
    rereview_note = (
        f"\n## REVIEW CYCLE {rcycle} (of up to {MAX_REVIEW_CYCLES})\n"
        "This is a re-review after a previous loopback. The full cross-loop "
        "narrative is in RUN HISTORY above; weigh whether the committee's "
        "prior concerns have been addressed in the latest paper draft.\n"
        if rcycle > 1
        else ""
    )
    history_ctx = history_block()

    thread = read_thread()
    cite_pool = [r["id"] for r in by_type(thread, "Citation") if r.get("verified")]
    relevant = ",".join(
        [r["id"] for r in by_type(thread, "Idea")]
        + [r["id"] for r in by_type(thread, "Hypothesis")]
        + [r["id"] for r in by_type(thread, "ExperimentResult")]
        + [r["id"] for r in by_type(thread, "Critique") if r.get("mode") == "validity"]
        + [r["id"] for r in by_type(thread, "Review")]
    )
    paper_rel = f"projects/{get_project_id()}/drafts/paper-vFINAL.md"
    valid_phases = ",".join(sorted(VALID_REVIEW_LOOPBACK_PHASES))

    jobs = []
    for persona in REVIEWER_PERSONAS:
        prompt = "\n".join(
            [
                "Phase: review",
                "Invoke skill: committee-reviewer",
                f"persona={persona['id']}",
                f"paper_path={paper_rel}",
                f"relevant_artifacts={relevant}",
                f"cite_pool={','.join(cite_pool) or '(none)'}",
                f"valid_loopback_phases={valid_phases}",
                "",
                history_ctx,
                rereview_note,
                "## Persona focus",
                "",
                persona["focus"],
                "",
                "Per the committee-reviewer skill, read the paper and the "
                "relevant artifacts, then emit ONE Review artifact via "
                "`python -m autolab.append_artifact --type Review` with the "
                "required fields (persona, recommendation, target_phase, "
                "score_overall, score_soundness, score_novelty, "
                "score_clarity) and the standard markdown body. End with the "
                "stdout contract.",
            ]
        )
        jobs.append(
            {
                "phase": "review",
                "skill": "committee-reviewer",
                "model": "fable",
                "prompt": prompt,
                "timeout_s": 1800,
            }
        )

    parallel_calls(jobs)
    refresh_indexes()

    last_ts = state["review_history"][-1]["ended_at"] if state.get("review_history") else None
    new_reviews = [
        r["id"]
        for r in by_type(read_thread(), "Review")
        if not last_ts or (r.get("created_at") or "") > last_ts
    ]
    log_line(f"review: cycle {rcycle} emitted {len(new_reviews)} review(s) {new_reviews}")
    return new_reviews


def cycle_state_path() -> Path:
    return checkpoints_dir().parent / "cycles.json"


def read_cycle_state() -> dict:
    """Combined cycle state for the experiment, idea, and review retreat loops.

    Schema:
      current        — experiment cycle (1-indexed), incremented on post-critique retreat
      history        — list of experiment-cycle endings: cycle, ended_at, failed_plan_ids, failed_hyp_ids, summary
      crash_retries  — { plan_id: count } orchestrator-level crash retries used
      idea_cycle     — idea cycle (1-indexed), incremented on post-screen wildness retreat
      idea_history   — list of idea-cycle endings: idea_cycle, ended_at, n_survivors, parked_hyp_ids
      review_cycle   — committee review cycle (1-indexed), incremented on post-review loopback
      review_history — list of review-cycle endings: review_cycle, ended_at, target_phase, recommendations, summary
    """
    defaults = {
        "current": 1,
        "history": [],
        "crash_retries": {},
        "idea_cycle": 1,
        "idea_history": [],
        "review_cycle": 1,
        "review_history": [],
        "run_design_cycle": 1,
        "run_design_history": [],
    }
    p = cycle_state_path()
    if not p.exists():
        return dict(defaults)
    try:
        s = json.loads(p.read_text())
        for k, v in defaults.items():
            s.setdefault(k, v)
        return s
    except json.JSONDecodeError:
        return dict(defaults)


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


def _retreat(
    *,
    counter_key: str,  # "current" | "idea_cycle" | "review_cycle"
    history_key: str,  # "history" | "idea_history" | "review_history"
    max_cycles: int,
    target_phase: str,  # phase to return on retreat
    wipe_from: str,  # phase to wipe checkpoints from
    label: str,  # log-line prefix
    decide,  # state -> (advance: bool, history_entry: dict | None)
    narrative_builder=None,  # (state, entry, thread) -> Markdown section to append to history.md
) -> str | None:
    """Generic retreat: shared cap check + structured-state history append +
    counter bump + checkpoint wipe + (NEW) Markdown-narrative append.

    `decide` inspects state/thread and returns:
      (True, _)        — no retreat; decide() logged its own reason.
      (False, entry)   — retreat; entry's `_log_extra` (if any) is appended to the
                         auto-generated retreat log line, then stripped before persist.

    `narrative_builder` (optional) takes (pre-bump state, structured entry,
    thread) and returns a Markdown section that is appended to
    `<project>/thread/history.md`. This is the canonical cross-loop context
    surface — every loopback hook should pass one of the
    `_history_entry_*` builders.
    """
    state = read_cycle_state()
    cycle = state.get(counter_key, 1)
    if max_cycles > 0 and cycle >= max_cycles:
        log_line(f"{label}: at MAX={max_cycles}; advancing past {target_phase}")
        return None
    advance, entry = decide(state)
    if advance:
        return None
    # Append the running-history entry BEFORE state mutation so the entry
    # builder sees the cycle that just ended, not the one about to begin.
    if narrative_builder is not None:
        try:
            md = narrative_builder(state, entry, read_thread())
            if md:
                append_history_entry(md)
        except Exception as e:  # noqa: BLE001
            log_line(f"{label}: failed to append history.md entry: {e}")
    entry = dict(entry or {})
    extra = entry.pop("_log_extra", "")
    state[history_key].append({**entry, counter_key: cycle, "ended_at": now_iso()})
    state[counter_key] = cycle + 1
    write_cycle_state(state)
    _wipe_checkpoints_from(wipe_from)
    log_line(
        f"{label}: cycle {cycle} → {cycle+1}; wiped from {wipe_from}"
        + (f"; {extra}" if extra else "")
    )
    return target_phase


def cycle_retreat_check() -> str | None:
    """Retreat after `critique` if no primary experiment passed."""

    def decide(state):
        cycle = state["current"]
        prev = state["history"][-1]["ended_at"] if state["history"] else None
        results = _experiment_results_after(prev)
        primary = [r for r in results if not r.get("is_ablation", False)]
        if not primary:
            log_line("retreat: no primary ExperimentResults found; not retreating")
            return True, None
        if any(r.get("status") == "pass" for r in primary):
            log_line(f"retreat: cycle {cycle} has pass result(s); advancing to write")
            return True, None
        plans_by_id = {p["id"]: p for p in by_type(read_thread(), "ExperimentPlan")}
        failed_plan_ids = [r.get("plan_id") for r in primary if r.get("plan_id")]
        failed_hyp_ids: list[str] = []
        for pid in failed_plan_ids:
            for parent in plans_by_id.get(pid, {}).get("parent_ids") or []:
                if parent.startswith("HYP-") and parent not in failed_hyp_ids:
                    failed_hyp_ids.append(parent)
        park_hypotheses(
            failed_hyp_ids,
            reason=f"cycle {cycle}: experiments did not produce a positive result",
        )
        return False, {
            "failed_plan_ids": failed_plan_ids,
            "failed_hyp_ids": failed_hyp_ids,
            "summary": f"{len(primary)} primary experiment(s), 0 pass",
            "_log_extra": f"parked {len(failed_hyp_ids)} HYPs ({failed_hyp_ids})",
        }

    return _retreat(
        counter_key="current",
        history_key="history",
        max_cycles=MAX_CYCLES,
        target_phase="survey",
        wipe_from="survey",
        label="retreat",
        decide=decide,
        narrative_builder=_history_entry_experiment_retreat,
    )


def review_loopback_check() -> str | None:
    """Aggregate the latest cycle's Review artifacts and decide whether to
    loop the orchestrator back to an earlier phase.

    Decision rules:
      - all `accept`              -> None  (paper ships)
      - any `major_revision`      -> earliest valid target_phase named by
                                     any reviewer; loops back via _retreat
      - mix of accept/minor only  -> None  (re-running just `final` already
                                     happened on the way here; minor
                                     revisions are advisory at this point)

    Capped by MAX_REVIEW_CYCLES; once at the cap, ships unconditionally.
    """

    def decide(state):
        cycle = state["review_cycle"]
        last_ts = state["review_history"][-1]["ended_at"] if state["review_history"] else None
        reviews = [
            r
            for r in by_type(read_thread(), "Review")
            if not last_ts or (r.get("created_at") or "") > last_ts
        ]
        if not reviews:
            log_line("review-retreat: no Review artifacts emitted; not looping back")
            return True, None
        recs = [r.get("recommendation", "accept") for r in reviews]
        if all(r == "accept" for r in recs):
            log_line(f"review-retreat: cycle {cycle} all-accept; shipping")
            return True, None

        targets = []
        for r in reviews:
            if r.get("recommendation") != "major_revision":
                continue
            tp = r.get("target_phase")
            if tp in VALID_REVIEW_LOOPBACK_PHASES:
                targets.append(tp)
        if not targets:
            log_line(
                f"review-retreat: cycle {cycle} recs={recs}; no valid loopback "
                "target_phase requested — treating as minor revision and shipping"
            )
            return True, None

        earliest = min(targets, key=PHASES.index)
        return False, {
            "n_reviews": len(reviews),
            "recommendations": recs,
            "target_phase": earliest,
            "summary": (
                f"{recs.count('major_revision')} major rev, "
                f"{recs.count('minor_revision')} minor, "
                f"{recs.count('accept')} accept; target={earliest}"
            ),
            "_log_extra": f"target={earliest}; recs={recs}",
        }

    state = read_cycle_state()
    if MAX_REVIEW_CYCLES > 0 and state.get("review_cycle", 1) >= MAX_REVIEW_CYCLES:
        log_line(f"review-retreat: at MAX={MAX_REVIEW_CYCLES}; shipping paper as-is")
        return None

    # We can't compute the target_phase upfront for the generic _retreat
    # helper (it depends on the reviews), so resolve it via decide() first
    # and pass through. Two-step pattern: peek at decide(), then dispatch.
    advance, entry = decide(state)
    if advance:
        return None
    target = entry["target_phase"]
    return _retreat(
        counter_key="review_cycle",
        history_key="review_history",
        max_cycles=MAX_REVIEW_CYCLES,
        target_phase=target,
        wipe_from=target,
        label="review-retreat",
        decide=lambda _state: (False, entry),
        narrative_builder=_history_entry_review_loopback,
    )


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
        log_line(
            f"crash-retry: re-running {pid} (orchestrator attempt {used+1}/{MAX_CRASH_RETRIES})"
        )
        # Surface any failure-analysis Critiques already filed against this
        # plan or its crashed RES so the retry sees the prior diagnosis
        # inline rather than having to discover it via Read.
        prior_fa: list[dict] = []
        for tid in (pid, latest.get("id")):
            if not tid:
                continue
            prior_fa.extend(_critiques_for(thread, tid, mode="failure-analysis"))
        prior_fa_block = ""
        if prior_fa:
            lines = [f"  └─ {_format_critique_one_line(c)}" for c in prior_fa]
            prior_fa_block = (
                "\n## PRIOR FAILURE-ANALYSIS (already diagnosed; address these)\n"
                + "\n".join(lines)
                + "\n"
            )
        prompt = (
            f"Phase: run-debug-retry\n"
            f"Invoke skill: experiment-runner\n"
            f"Target: {pid}\n"
            f"Crashed result: {latest.get('id', '?')}\n"
            f"Attempt: {used+1} of {MAX_CRASH_RETRIES} (orchestrator-level)\n\n"
            f"{prior_fa_block}"
            f"PRIOR ATTEMPT CRASHED. Read thoughts/{pid}.md, the latest "
            f"experiments/{pid}/runs/*.log, and any failure-analysis Critiques "
            f"(summarized above if present). "
            f"Per the experiment-runner skill, diagnose the crash, edit "
            f"experiments/{pid}/code/run.py to address the root cause "
            f"(common: hyperparam out of range, dtype mismatch, OOM, missing import, "
            f"shape error). Re-run with sanity gate then full sweep. Emit a fresh "
            f"ExperimentResult. End with the stdout contract."
        )
        call_claude("run-debug-retry", "experiment-runner", "fable", prompt, timeout_s=2400)
        refresh_indexes()
        retries_done += 1
    return retries_done


# ---------------------------------------------------------------------------
# Run history (single source of truth for cross-loop context).
#
# Every loopback (experiment retreat, idea retreat, review loopback) appends
# one short, deterministically-templated section to `<project>/thread/history.md`
# describing what was tried, what didn't work, and why we looped back. Every
# phase that may run as part of a loopback injects the entire history.md as
# a prompt prefix via `history_block()`, so skills always see the running
# narrative — across loops, across cycles, in order — with pointers to the
# raw artifacts they can `Read` for full detail.
#
# This replaced an earlier per-loop architecture (one custom context-builder
# per loopback type) that didn't compound across cycles and duplicated logic.
# ---------------------------------------------------------------------------

HISTORY_BUDGET_CHARS = 8000


def _truncate_one_line(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _hyp_claim(thread: list[dict], hyp_id: str) -> str:
    """Best-effort one-line claim for a HYP id (used in history entries)."""
    for r in thread:
        if r.get("type") == "Hypothesis" and r.get("id") == hyp_id:
            claim = r.get("claim") or r.get("summary") or ""
            return _truncate_one_line(claim, 120)
    return "(claim not found)"


def _critiques_for(thread: list[dict], target_id: str, mode: str | None = None) -> list[dict]:
    """Return Critique rows targeting `target_id` (optionally filtered by mode)."""
    out = []
    for r in thread:
        if r.get("type") != "Critique":
            continue
        if r.get("target_id") != target_id:
            continue
        if mode is not None and r.get("mode") != mode:
            continue
        out.append(r)
    return out


def _format_critique_one_line(crit: dict) -> str:
    """Render a Critique as one short line for history entries."""
    cid = crit.get("id", "?")
    mode = crit.get("mode") or "?"
    sev = crit.get("severity") or "?"
    concerns = crit.get("concerns") or []
    if isinstance(concerns, str):
        try:
            concerns = json.loads(concerns)
        except json.JSONDecodeError:
            concerns = [concerns]
    if not isinstance(concerns, list):
        concerns = [str(concerns)]
    head = "; ".join(_truncate_one_line(str(c), 100) for c in concerns[:2]) or crit.get(
        "summary", ""
    )
    return f"{cid} ({mode}, severity={sev}): {head}"


def append_history_entry(entry_text: str) -> None:
    """Append a Markdown section to `<project>/thread/history.md`.

    Entries are written deterministically by the loopback hooks (no LLM
    call) so the running narrative stays cheap, structured, and consistent.
    Empty/whitespace inputs are ignored.
    """
    if not entry_text or not entry_text.strip():
        return
    p = history_log()
    p.parent.mkdir(parents=True, exist_ok=True)
    sep = "" if not p.exists() or p.read_text().endswith("\n\n") else "\n"
    with p.open("a") as f:
        f.write(sep + entry_text.rstrip() + "\n\n")


def history_block(max_chars: int = HISTORY_BUDGET_CHARS) -> str:
    """Return the running history.md as a prompt prefix.

    Injected by every phase that may run as part of a loopback. Returns "" on
    a virgin project so first-run prompts are unaffected. If the file is
    larger than `max_chars` (default ~2k tokens), only the most recent
    portion is kept, with an explicit elision note prepended so the skill
    knows older context exists on disk.
    """
    p = history_log()
    if not p.exists():
        return ""
    text = p.read_text()
    if not text.strip():
        return ""
    elided = ""
    if len(text) > max_chars:
        text = text[-max_chars:]
        elided = (
            "_[earlier entries elided to fit prompt budget; full log lives at "
            "`<project>/thread/history.md`]_\n\n"
        )
    return (
        "\n## RUN HISTORY (groomed, append-only)\n\n"
        "Cross-loop narrative of every retreat / loopback so far. Each entry "
        "lists what was tried, the parked artifact ids (HYP-/REV-/CRIT-), and "
        "what the next phase should do about it. Read referenced artifact ids "
        "for full bodies.\n\n"
        f"{elided}{text.rstrip()}\n"
    )


def _history_entry_experiment_retreat(state: dict, entry: dict, thread: list[dict]) -> str:
    """Templated history section for an experiment retreat.

    `entry` is the structured dict that `cycle_retreat_check.decide()` built
    (failed_plan_ids, failed_hyp_ids, summary). `state` is read pre-bump so
    `state["current"]` is the cycle that just ended.
    """
    cycle = state.get("current", 1)
    failed_hyps = entry.get("failed_hyp_ids", []) or []
    failed_plans = entry.get("failed_plan_ids", []) or []
    summary = entry.get("summary") or ""
    lines = [
        f"### Cycle {cycle} ended ({now_iso()}) — experiment retreat → survey",
        "",
        f"{summary or 'Previous cycle yielded no positive results.'} "
        "Orchestrator parked the failed HYPs and is re-running from `survey`.",
        "",
        "Failed HYPs (parked, do not re-propose variations):",
    ]
    if failed_hyps:
        for hid in failed_hyps:
            lines.append(f'  - **{hid}** "{_hyp_claim(thread, hid)}"')
            for c in _critiques_for(thread, hid, mode="validity"):
                lines.append(f"    └─ {_format_critique_one_line(c)}")
    else:
        lines.append("  (none recorded)")
    lines.append("")
    lines.append(f"Failed ExperimentPlans: {failed_plans or '(none)'}")
    lines.append("")
    lines.append(
        "**Next:** propose materially different angles in survey/design — "
        "not variations of the parked HYPs above. Read parked HYP bodies and "
        "linked ExperimentResult / Critique artifacts for the full picture."
    )
    return "\n".join(lines)


def _history_entry_idea_retreat(state: dict, entry: dict, thread: list[dict]) -> str:
    """Templated history section for an idea retreat (post-screen wildness fail)."""
    icycle = state.get("idea_cycle", 1)
    parked = entry.get("parked_hyp_ids", []) or []
    n_survivors = entry.get("n_survivors", 0)
    lines = [
        f"### Idea-cycle {icycle} ended ({now_iso()}) — idea retreat → expand",
        "",
        f"Only {n_survivors} HYP(s) cleared the wildness bar. Boring ones parked.",
        "",
        "Parked HYPs (do not regenerate variations):",
    ]
    if parked:
        for hid in parked:
            lines.append(f'  - **{hid}** "{_hyp_claim(thread, hid)}"')
            for c in _critiques_for(thread, hid, mode="boredom"):
                lines.append(f"    └─ {_format_critique_one_line(c)}")
    else:
        lines.append("  (none recorded)")
    lines.append("")
    lines.append(
        "**Next:** push hard into Wildness Tickets W1 (NON-ML cross-domain) "
        "and W2 (textbook contradiction). If your draft hypothesis would not "
        "surprise a sharp PhD student, throw it out before emitting."
    )
    return "\n".join(lines)


def _history_entry_review_loopback(state: dict, entry: dict, thread: list[dict]) -> str:
    """Templated history section for a committee review loopback."""
    rcycle = state.get("review_cycle", 1)
    target = entry.get("target_phase") or "?"
    summary = entry.get("summary") or ""
    recs = entry.get("recommendations", []) or []
    # Reviews from this just-ended cycle: created since the previous review_history entry.
    prior = state.get("review_history") or []
    last_ts = prior[-1]["ended_at"] if prior else None
    cycle_reviews = [
        r for r in by_type(thread, "Review") if not last_ts or (r.get("created_at") or "") > last_ts
    ]

    lines = [
        f"### Review cycle {rcycle} ended ({now_iso()}) — review loopback → {target}",
        "",
        f"Committee voted: {summary or recs}. Looping back to `{target}`.",
        "",
        "Per-persona verdicts:",
    ]
    if cycle_reviews:
        for r in cycle_reviews:
            persona = r.get("persona", "?")
            rec = r.get("recommendation", "?")
            tp = r.get("target_phase", "")
            marker = f" → wants `{tp}`" if rec == "major_revision" and tp else ""
            sm = _truncate_one_line(r.get("summary") or "", 140)
            sm_tail = f" — {sm}" if sm else ""
            lines.append(f"  - **{persona}** ({r['id']}) {rec}{marker}{sm_tail}")
    else:
        lines.append("  (no per-persona summary available)")
    lines.append("")
    lines.append(
        f"**Next:** address every `major_revision` concern explicitly when "
        f"re-running `{target}` (and downstream phases). Read the full Review "
        f"bodies in `thoughts/REV-NNN.md` for specific concerns and requested "
        f"changes. Advisory `minor_revision` feedback should be considered "
        f"but is not blocking."
    )
    return "\n".join(lines)


def idea_retreat_check() -> str | None:
    """Retreat after `screen` if too few hypotheses cleared the wildness bar."""

    def decide(state):
        n = len(surviving_hypotheses())
        if n >= MIN_WILD_HYPOTHESES:
            log_line(f"idea-retreat: {n} survivor(s) ≥ {MIN_WILD_HYPOTHESES}; advancing to design")
            return True, None
        thread = read_thread()
        hyps = {h["id"]: h for h in by_type(thread, "Hypothesis")}
        parked: list[str] = []
        for crit in by_type(thread, "Critique"):
            if (
                crit.get("severity") == "high"
                and crit.get("mode") == "boredom"
                and crit.get("target_id", "").startswith("HYP-")
                and crit["target_id"] in hyps
                and crit["target_id"] not in parked
            ):
                parked.append(crit["target_id"])
        return False, {
            "n_survivors": n,
            "parked_hyp_ids": parked,
            "_log_extra": (
                f"only {n} wild survivor(s) (need ≥ {MIN_WILD_HYPOTHESES}); "
                f"parked {len(parked)} HYPs ({parked})"
            ),
        }

    return _retreat(
        counter_key="idea_cycle",
        history_key="idea_history",
        max_cycles=MAX_IDEA_CYCLES,
        target_phase="expand",
        wipe_from="expand",
        label="idea-retreat",
        decide=decide,
        narrative_builder=_history_entry_idea_retreat,
    )


def run_positive_result_check() -> str | None:
    """After `run`, check that at least one primary experiment produced a positive
    result. If not, loop back to `design` so the experiment design can be
    re-investigated before giving up on the hypotheses entirely.

    This is a lighter-weight retreat than the post-critique `cycle_retreat_check`
    which parks the hypotheses and retreats all the way to `survey`. Here we
    keep the hypotheses alive and just redo the experiment design.
    """

    def decide(state):
        cycle = state.get("run_design_cycle", 1)
        thread = read_thread()
        results = by_type(thread, "ExperimentResult")
        primary = [r for r in results if not r.get("is_ablation", False)]
        if not primary:
            log_line("run-positive-check: no primary ExperimentResults found; not retreating")
            return True, None
        if any(r.get("status") == "pass" for r in primary):
            log_line(
                f"run-positive-check: cycle {cycle} has ≥1 positive result; "
                "advancing to critique"
            )
            return True, None
        # No positive results — loop back to design to re-investigate
        failed_plan_ids = list({r.get("plan_id") for r in primary if r.get("plan_id")})
        return False, {
            "n_primary": len(primary),
            "failed_plan_ids": failed_plan_ids,
            "summary": (
                f"{len(primary)} primary experiment(s) ran, 0 positive results; "
                "re-investigating experiment design"
            ),
            "_log_extra": f"0/{len(primary)} positive; redesigning {failed_plan_ids}",
        }

    return _retreat(
        counter_key="run_design_cycle",
        history_key="run_design_history",
        max_cycles=MAX_RUN_DESIGN_CYCLES,
        target_phase="design",
        wipe_from="design",
        label="run-positive-check",
        decide=decide,
        narrative_builder=_history_entry_run_redesign,
    )


def _history_entry_run_redesign(state: dict, entry: dict, thread: list[dict]) -> str:
    """Templated history section for a run→design retreat (no positive results)."""
    cycle = state.get("run_design_cycle", 1)
    n_primary = entry.get("n_primary", 0)
    failed_plans = entry.get("failed_plan_ids", []) or []
    summary = entry.get("summary") or ""
    lines = [
        f"### Run-design cycle {cycle} ended ({now_iso()}) — no positive results → design",
        "",
        f"{summary or f'{n_primary} experiments ran with no positive results.'} "
        "Orchestrator is looping back to `design` to re-investigate the "
        "experiment design before abandoning these hypotheses.",
        "",
        "Failed experiment plans (redesign with different approach):",
    ]
    if failed_plans:
        plans_by_id = {p["id"]: p for p in by_type(thread, "ExperimentPlan")}
        for pid in failed_plans:
            plan = plans_by_id.get(pid, {})
            psummary = _truncate_one_line(plan.get("summary", ""), 120)
            lines.append(f"  - **{pid}**: {psummary}")
    else:
        lines.append("  (none recorded)")
    lines.append("")
    lines.append(
        "**Next:** redesign experiments with a different approach — consider "
        "different hyperparameters, different baselines, different evaluation "
        "metrics, or a fundamentally different experimental setup. The hypotheses "
        "are still viable; the experiment design needs revision."
    )
    return "\n".join(lines)


def next_phase_to_run(args) -> str | None:
    cp = latest_checkpoint()
    if cp is None:
        return "seed" if args.idea else None
    cur = cp.get("phase", "seed")
    # Idea-retreat hook: after screen, if too few hypotheses cleared the wildness
    # bar, loop back to expand for a wilder batch.
    if cur == "screen":
        retreat = idea_retreat_check()
        if retreat:
            return retreat
    # Run-positive-result hook: after run, if no experiment produced a positive
    # result, loop back to design to re-investigate the experiment design.
    if cur == "run":
        retreat = run_positive_result_check()
        if retreat:
            return retreat
    # Experiment-retreat hook: after critique, if no positive result, loop back
    # to survey for new hypotheses.
    if cur == "critique":
        retreat = cycle_retreat_check()
        if retreat:
            return retreat
    # Review-loopback hook: after the committee review, if a major revision
    # was requested, loop back to the earliest target phase.
    if cur == "review":
        loopback = review_loopback_check()
        if loopback:
            return loopback
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
    elif phase == "thought-experiment":
        ids = phase_thought_experiment()
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
    elif phase == "review":
        ids = phase_review()
    else:
        raise SystemExit(f"unknown phase: {phase}")
    write_checkpoint(
        phase,
        ids,
        None if phase == PHASES[-1] else PHASES[PHASES.index(phase) + 1],
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
        phase = next_phase_to_run(args)
        if phase is None:
            stop_reason = stop_conditions_met()
            if stop_reason:
                log_line(f"stop: {stop_reason}")
            else:
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
