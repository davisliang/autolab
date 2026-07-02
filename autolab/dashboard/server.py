#!/usr/bin/env python3
"""autolab progress dashboard.

Single-file stdlib HTTP server that reads directly from `projects/<id>/` and
renders a live-refreshing web view of every run's progress.

Usage:
    uv run python -m autolab.dashboard.server            # http://localhost:8765
    uv run python -m autolab.dashboard.server --port 9000
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from autolab.paths import (
    PROJECTS,
    checkpoints_dir,
    cost_ledger,
    drafts_dir,
    experiments_dir,
    history_log,
    list_projects,
    orchestrator_log,
    papers_index,
    parking_lot,
    thoughts_dir,
    thread_log,
)

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

# One short description per phase, surfaced as a hover tooltip on each phase
# pill in the dashboard. Keep these terse — they render via the native
# `title=""` attribute, which has no formatting and clips long text.
PHASE_DESCRIPTIONS = {
    "seed": (
        "Reads your --idea and emits one Idea artifact. No LLM call; the "
        "orchestrator does this directly."
    ),
    "expand": (
        "idea-expander emits 3–5 Hypotheses, each with a pre-registered "
        "numeric prediction and a wildness ticket (W1–W4). At least one "
        "must be a cross-domain transplant from a non-ML field."
    ),
    "survey": (
        "literature-scout fans out one parallel call per Hypothesis, "
        "fetches 3–7 papers from HF/arXiv per query, and emits "
        "LitFinding rows referencing the cached paper markdown."
    ),
    "gap-fill": (
        "idea-expander runs again in negative-space mode and adds 1–2 "
        "more Hypotheses targeting questions the LitFinding set "
        "conspicuously misses."
    ),
    "screen": (
        "Two parallel passes per Hypothesis: critic in 'boredom' mode "
        "argues against each claim, and novelty-checker fuzzy-matches "
        "titles against the survey results. High-severity HYPs are "
        "parked. Triggers idea retreat if too few survive."
    ),
    "thought-experiment": (
        "thought-experimenter rolls out a deliberate toy problem per "
        "surviving Hypothesis — pure reasoning, no compute. It isolates "
        "the mechanism, simulates it against the null, names failure "
        "modes, and renders a verdict (promising / inconclusive / "
        "refuted). Scalability is contemplated only after the toy "
        "rollout. Refuted hypotheses are parked and never reach design."
    ),
    "design": (
        "experiment-designer emits one ExperimentPlan per surviving "
        "Hypothesis, building the first informative (non-toy) step beyond "
        "the thought experiment's toy problem. Each plan must include ≥3 "
        "seeds and a matched-budget baseline; missing fields are rejected "
        "by the runner."
    ),
    "run": (
        "experiment-runner sanity-gates each plan (32-example overfit), "
        "then executes the multi-seed proposed + baseline sweep with "
        "logged stdout and a hard timeout. Passing experiments trigger "
        "exactly one auto-ablation isolating the proposed mechanism."
    ),
    "critique": (
        "critic in 'validity' mode reviews each ExperimentResult for "
        "threats to validity, baseline parity, statistical concerns. "
        "If no primary result passes, triggers the experiment retreat "
        "back to survey."
    ),
    "write": (
        "paper-writer produces the paper section by section (outline → "
        "abstract → intro → related → background → data/models → method "
        "→ experiments → discussion → conclusion → broader-impact → "
        "reproducibility). Each section is a separate claude -p call "
        "and may only cite verified Citation rows."
    ),
    "final": (
        "Orchestrator stitches all DraftSection bodies into "
        "drafts/paper-vFINAL.md, then paper-polisher does a "
        "completeness + clarity pass: fills any '_(missing)_' "
        "sections, tightens weak prose, enforces "
        "intro-contributions ↔ experiments-table consistency. The "
        "pre-polish version is kept at paper-vFINAL.pre-polish.md."
    ),
    "review": (
        "3 committee personas (methodologist, domain-expert, "
        "clarity-reviewer) read the polished paper in parallel and "
        "each emits one Review artifact with a recommendation "
        "(accept / minor_revision / major_revision) plus four "
        "1–10 scores. Any 'major_revision' with a valid target_phase "
        "loops the orchestrator back to that phase. Capped by "
        "AUTOLAB_MAX_REVIEW_CYCLES."
    ),
}

# Static dashboard HTML lives next to this file. Read on each request so editing
# the file shows up after a browser refresh — no server restart needed.
STATIC_INDEX = Path(__file__).resolve().parent / "static" / "index.html"


def safe_read(p: Path, max_bytes: int = 200_000) -> str:
    if not p.exists() or not p.is_file():
        return ""
    data = p.read_bytes()
    if len(data) > max_bytes:
        data = data[-max_bytes:]
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def tail_lines(p: Path, n: int = 200) -> list[str]:
    if not p.exists():
        return []
    with p.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        block = 8192
        data = b""
        while size > 0 and data.count(b"\n") <= n:
            step = min(block, size)
            size -= step
            f.seek(size)
            data = f.read(step) + data
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return lines[-n:]


def parse_ledger(p: Path) -> dict:
    """Parse the token ledger. Tolerates three historical schemas:

    - 8-col current: ts, phase, skill, model, input_fresh, cache_create, cache_read, output
    - 7-col legacy: ts, phase, skill, model, input_total, output, usd  (USD ignored)
    - 6-col legacy: ts, phase, skill, model, input_total, output

    Returns aggregates with cache breakdown so the dashboard can show hit rate.
    """
    empty_bucket = lambda: {
        "calls": 0,
        "fresh_in": 0,
        "cache_create": 0,
        "cache_read": 0,
        "in_tokens": 0,
        "out_tokens": 0,
    }
    if not p.exists():
        return {
            "rows": [],
            "total_fresh_in": 0,
            "total_cache_create": 0,
            "total_cache_read": 0,
            "total_in_tokens": 0,
            "total_out_tokens": 0,
            "cache_hit_ratio": 0.0,
            "by_phase": {},
            "by_model": {},
        }
    rows = []
    totals = {"fresh_in": 0, "cache_create": 0, "cache_read": 0, "in_tokens": 0, "out_tokens": 0}
    by_phase: dict[str, dict] = {}
    by_model: dict[str, dict] = {}
    with p.open() as f:
        next(f, None)  # header
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            ts, phase, skill, model = parts[:4]
            try:
                if len(parts) >= 8:
                    fresh = int(parts[4])
                    cc = int(parts[5])
                    cr = int(parts[6])
                    out = int(parts[7])
                else:
                    # 6 or 7 col legacy: column 4 already holds total input, no cache split
                    fresh = int(parts[4])
                    cc = 0
                    cr = 0
                    out = int(parts[5])
            except ValueError:
                continue
            in_total = fresh + cc + cr
            rows.append(
                {
                    "ts": ts,
                    "phase": phase,
                    "skill": skill,
                    "model": model,
                    "fresh_in": fresh,
                    "cache_create": cc,
                    "cache_read": cr,
                    "input_tokens": in_total,
                    "output_tokens": out,
                }
            )
            totals["fresh_in"] += fresh
            totals["cache_create"] += cc
            totals["cache_read"] += cr
            totals["in_tokens"] += in_total
            totals["out_tokens"] += out
            for bucket, key in ((by_phase, phase), (by_model, model)):
                d = bucket.setdefault(key, empty_bucket())
                d["calls"] += 1
                d["fresh_in"] += fresh
                d["cache_create"] += cc
                d["cache_read"] += cr
                d["in_tokens"] += in_total
                d["out_tokens"] += out
    hit_ratio = totals["cache_read"] / totals["in_tokens"] if totals["in_tokens"] else 0.0
    return {
        "rows": rows[-50:],
        "total_fresh_in": totals["fresh_in"],
        "total_cache_create": totals["cache_create"],
        "total_cache_read": totals["cache_read"],
        "total_in_tokens": totals["in_tokens"],
        "total_out_tokens": totals["out_tokens"],
        "cache_hit_ratio": hit_ratio,
        "by_phase": by_phase,
        "by_model": by_model,
    }


def list_checkpoints(pid: str) -> list[dict]:
    d = checkpoints_dir(pid)
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        out.append(
            {
                "phase": data.get("phase", f.stem),
                "completed_artifact_ids": data.get("completed_artifact_ids", []),
                "next_action": data.get("next_action"),
                "completed_at": data.get("completed_at"),
            }
        )
    return out


def current_phase(pid: str) -> str | None:
    cps = {c["phase"] for c in list_checkpoints(pid)}
    if not cps:
        return None
    if "final" in cps:
        return "final"
    for ph in PHASES:
        if ph not in cps:
            return ph
    return PHASES[-1]


_FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_thought(p: Path) -> dict:
    text = safe_read(p, 50_000)
    title = p.stem
    summary = ""
    m = _FRONT_MATTER_RE.match(text)
    if m:
        body = text[m.end() :].strip()
    else:
        body = text.strip()
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip() or title
            continue
        if line and not line.startswith("#"):
            summary = line[:240]
            break
    mtime = p.stat().st_mtime if p.exists() else 0
    return {
        "id": p.stem,
        "title": title,
        "summary": summary,
        "mtime": mtime,
        "path": str(p.relative_to(PROJECTS.parent)),
    }


def list_thoughts(pid: str) -> list[dict]:
    d = thoughts_dir(pid)
    if not d.exists():
        return []
    return sorted(
        [parse_thought(p) for p in d.glob("*.md")],
        key=lambda r: r["id"],
    )


def list_drafts(pid: str) -> list[dict]:
    d = drafts_dir(pid)
    if not d.exists():
        return []
    out = []
    for p in sorted(d.iterdir()):
        if not p.is_file():
            continue
        st = p.stat()
        out.append(
            {
                "name": p.name,
                "size": st.st_size,
                "mtime": st.st_mtime,
            }
        )
    return out


def list_experiments(pid: str) -> list[dict]:
    d = experiments_dir(pid)
    if not d.exists():
        return []
    out = []
    for p in sorted(d.iterdir()):
        if not p.is_dir():
            continue
        st = p.stat()
        out.append({"name": p.name, "mtime": st.st_mtime})
    return out


_LOG_BEGIN_RE = re.compile(r"=== begin phase: ([\w-]+) ===")
_LOG_END_RE = re.compile(r"=== end phase: ([\w-]+)")
_LOG_CALL_BEGIN_RE = re.compile(r"call_claude phase=(\S+) skill=(\S+) model=(\S+)")
_LOG_CALL_EXIT_RE = re.compile(r"call_claude exit=(\d+) phase=(\S+) skill=(\S+)")
_LOG_CALL_TIMEOUT_RE = re.compile(r"call_claude TIMEOUT phase=(\S+) skill=(\S+)")
_LOG_TS_RE = re.compile(r"^\[([^\]]+)\]")


def live_status(pid: str) -> dict:
    """Scan orchestrator.log for in-flight phase + claude calls.

    A phase is "running" if its `=== begin ===` line has no matching `=== end ===`.
    A claude call is "in-flight" if its `call_claude phase=X skill=Y` has no
    matching `call_claude exit=` or `TIMEOUT` line after it.
    """
    lines = tail_lines(orchestrator_log(pid), 2000)
    running_phase: str | None = None
    phase_started_at: str | None = None
    inflight_calls: list[dict] = []
    last_event_ts: str | None = None
    for line in lines:
        ts_m = _LOG_TS_RE.match(line)
        ts = ts_m.group(1) if ts_m else None
        if ts:
            last_event_ts = ts
        m = _LOG_BEGIN_RE.search(line)
        if m:
            running_phase = m.group(1)
            phase_started_at = ts
            continue
        m = _LOG_END_RE.search(line)
        if m and m.group(1) == running_phase:
            running_phase = None
            phase_started_at = None
            continue
        m = _LOG_CALL_BEGIN_RE.search(line)
        if m:
            inflight_calls.append(
                {
                    "phase": m.group(1),
                    "skill": m.group(2),
                    "model": m.group(3),
                    "started_at": ts,
                }
            )
            continue
        m = _LOG_CALL_EXIT_RE.search(line) or _LOG_CALL_TIMEOUT_RE.search(line)
        if m:
            ph, sk = (
                (m.group(2), m.group(3)) if m.re is _LOG_CALL_EXIT_RE else (m.group(1), m.group(2))
            )
            for i in range(len(inflight_calls) - 1, -1, -1):
                c = inflight_calls[i]
                if c["phase"] == ph and c["skill"] == sk:
                    del inflight_calls[i]
                    break
    return {
        "running_phase": running_phase,
        "phase_started_at": phase_started_at,
        "inflight_calls": inflight_calls,
        "last_event_ts": last_event_ts,
    }


def _truncate(s, n: int = 320) -> str:
    s = str(s) if s is not None else ""
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def event_decision_summary(ev: dict) -> str:
    """Build a few-sentence summary showing what the model decided/produced.

    Pulls from type-specific fields the subagent emitted (status, severity,
    mode, concerns, prediction_*, claim, notes, etc.), not just `summary`.
    """
    t = ev.get("type", "") or ""
    summary = ev.get("summary") or ""

    if t == "Idea":
        framing = ev.get("framing") or ""
        oq = ev.get("open_questions") or []
        parts = [_truncate(summary, 280)]
        if framing and framing != summary:
            parts.append(f"Framing: {_truncate(framing, 240)}")
        if isinstance(oq, list) and oq:
            parts.append("Open questions: " + "; ".join(_truncate(q, 80) for q in oq[:3]))
        return "\n".join(p for p in parts if p)

    if t == "Hypothesis":
        claim = ev.get("claim") or summary
        metric = ev.get("prediction_metric") or ""
        thr = ev.get("prediction_threshold")
        direction = ev.get("prediction_direction") or ""
        parts = [f"**Claim:** {_truncate(claim, 280)}"]
        if metric:
            thr_str = "" if thr in (None, "") else f" threshold {thr}"
            parts.append(f"**Predicts:** `{metric}` {direction}{thr_str}".strip())
        wt = ev.get("wildness_tickets") or ev.get("wildness_ticket")
        if wt:
            parts.append(f"**Wildness:** {wt}")
        return "\n".join(parts)

    if t == "ThoughtExperiment":
        verdict = (ev.get("verdict") or "?").strip()
        hid = ev.get("hypothesis_id") or ""
        marker = {
            "promising": "✓ promising",
            "inconclusive": "~ inconclusive",
            "refuted": "✗ refuted",
        }.get(verdict.lower(), verdict)
        parts = [f"**{marker}**" + (f" for `{hid}`" if hid else "")]
        toy = ev.get("toy_problem") or ""
        if toy:
            parts.append(f"**Toy problem:** {_truncate(toy, 220)}")
        pred = ev.get("predicted_outcome") or ""
        if pred:
            parts.append(f"**Predicts:** {_truncate(pred, 200)}")
        scale = ev.get("scalability_note") or ""
        if scale and verdict.lower() != "refuted":
            parts.append(f"**Next (toward scale):** {_truncate(scale, 200)}")
        return "\n".join(parts)

    if t == "LitFinding":
        finding = ev.get("finding") or summary
        arxiv = ev.get("arxiv_id") or ""
        head = f"[{arxiv}] " if arxiv else ""
        return head + _truncate(finding, 320)

    if t == "Critique":
        mode = ev.get("mode") or "?"
        severity = ev.get("severity") or "?"
        target = ev.get("target_id") or ""
        concerns = ev.get("concerns") or []
        if isinstance(concerns, str):
            try:
                concerns = json.loads(concerns)
            except json.JSONDecodeError:
                concerns = [concerns]
        if not isinstance(concerns, list):
            concerns = [str(concerns)]
        bullets = "; ".join(_truncate(c, 120) for c in concerns[:4])
        fix = ev.get("proposed_fix") or ""
        parts = [f"**[{mode}, severity={severity}]** target=`{target}`"]
        if bullets:
            parts.append(f"Concerns: {bullets}")
        if fix:
            parts.append(f"Proposed fix: {_truncate(fix, 200)}")
        return "\n".join(parts)

    if t == "ExperimentPlan":
        budget = ev.get("compute_budget_minutes")
        seeds = ev.get("seeds") or []
        ablation = ev.get("is_ablation", False)
        head_bits = []
        if ablation:
            head_bits.append("ABLATION")
        if seeds:
            head_bits.append(f"seeds={seeds}")
        if budget:
            head_bits.append(f"budget={budget}min")
        head = " · ".join(head_bits)
        out = f"**[{head}]**\n" if head else ""
        return out + _truncate(summary, 320)

    if t == "ExperimentResult":
        status = ev.get("status") or "?"
        plan_id = ev.get("plan_id") or ""
        notes = ev.get("notes") or ""
        marker = {"pass": "✓ pass", "fail": "✗ fail", "crash": "⚠ crash"}.get(status, status)
        parts = [f"**{marker}** for `{plan_id}`"]
        if summary and summary != notes:
            parts.append(_truncate(summary, 240))
        if notes:
            parts.append(_truncate(notes, 480))
        return "\n".join(parts)

    if t == "Citation":
        verified = bool(ev.get("verified"))
        target = ev.get("target_id") or "?"
        arxiv = ev.get("arxiv_id") or ""
        mark = "✓ verified" if verified else "✗ unverified"
        return f"{mark} citation for `{target}`" + (f" — arxiv:{arxiv}" if arxiv else "")

    if t == "DraftSection":
        sec = ev.get("section") or "?"
        ver = ev.get("version") or "?"
        bp = ev.get("body_path") or ""
        return f"`{sec}` v{ver}" + (f" → {bp}" if bp else "")

    if t == "Review":
        persona = ev.get("persona") or "?"
        rec = ev.get("recommendation") or "?"
        target = ev.get("target_phase") or ""
        marker = {
            "accept": "✓ accept",
            "minor_revision": "~ minor",
            "major_revision": "✗ major",
        }.get(rec, rec)
        scores = []
        for k in ("score_overall", "score_soundness", "score_novelty", "score_clarity"):
            v = ev.get(k)
            if v not in (None, ""):
                scores.append(f"{k.replace('score_', '')}={v}")
        head = f"**[{persona}]** {marker}"
        if rec == "major_revision" and target:
            head += f" → loop back to `{target}`"
        parts = [head]
        if scores:
            parts.append(" · ".join(scores))
        if summary:
            parts.append(_truncate(summary, 240))
        return "\n".join(parts)

    # Unknown type: just trust summary
    return _truncate(summary, 320)


def parse_thread_events(pid: str, n: int = 80) -> list[dict]:
    p = thread_log(pid)
    if not p.exists():
        return []
    out: list[dict] = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            out.append(
                {
                    "id": ev.get("id"),
                    "type": ev.get("type"),
                    "author": ev.get("author"),
                    "summary": (ev.get("summary") or "")[:240],
                    "decision": event_decision_summary(ev),
                    "ts": ev.get("ts") or ev.get("created_at"),
                    "parent_ids": ev.get("parent_ids") or [],
                }
            )
    return out[-n:][::-1]


def read_cycles(pid: str) -> dict:
    p = thoughts_dir(pid).parent / "thread" / "cycles.json"
    if not p.exists():
        return {"current": 1, "history": [], "crash_retries": {}}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {"current": 1, "history": [], "crash_retries": {}}


def project_summary(pid: str) -> dict:
    cps = list_checkpoints(pid)
    ledger = parse_ledger(cost_ledger(pid))
    # "Last activity" is the most recent mtime across every signal a running
    # subagent might touch: orchestrator log (phase boundaries), thread log
    # (artifact emissions during long subagent calls), the cost ledger, and the
    # newest thoughts/* file.
    candidates: list[float] = []
    for p in (
        orchestrator_log(pid),
        thread_log(pid),
        cost_ledger(pid),
    ):
        if p.exists():
            candidates.append(p.stat().st_mtime)
    td = thoughts_dir(pid)
    if td.exists():
        for f in td.glob("*.md"):
            try:
                candidates.append(f.stat().st_mtime)
            except OSError:
                pass
    last_log_ts = max(candidates) if candidates else None
    cy = read_cycles(pid)
    return {
        "id": pid,
        "current_phase": current_phase(pid),
        "completed_phases": [c["phase"] for c in cps],
        "all_phases": PHASES,
        "phase_descriptions": PHASE_DESCRIPTIONS,
        "total_in_tokens": ledger["total_in_tokens"],
        "total_out_tokens": ledger["total_out_tokens"],
        "n_calls": sum(v["calls"] for v in ledger["by_phase"].values()),
        "last_activity_ts": last_log_ts,
        "cycle": cy.get("current", 1),
        "n_retreats": len(cy.get("history", [])),
        "idea_cycle": cy.get("idea_cycle", 1),
        "n_idea_retreats": len(cy.get("idea_history", [])),
    }


def _load_full_thread(pid: str) -> list[dict]:
    """Read every record from thread/log.jsonl with full fields."""
    p = thread_log(pid)
    if not p.exists():
        return []
    out: list[dict] = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# ---------------------------------------------------------------------------
# Project narrative — human-readable, chronologically ordered story of the
# project's progress. Synthesizes thread artifacts + phase checkpoints +
# history.md (loopback narrative) into one stream of plain-English events
# meant for casual reading: "looked up papers", "came up with N ideas",
# "experiment failed because Y", "committee asked for design changes".
# ---------------------------------------------------------------------------

_HISTORY_HEADER_RE = re.compile(r"^### (.+)$")
_HISTORY_TS_RE = re.compile(r"\(([0-9T:+\-]+)\)")


def _parse_history_md_entries(text: str) -> list[dict]:
    """Split a history.md document into its `### ...` sections.

    Returns a list of {ts, header, body} dicts. `ts` is parsed from the
    `(YYYY-MM-DDThh:mm:ss…)` substring of the header; missing / unparseable
    timestamps fall through as None.
    """
    if not text:
        return []
    entries: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        m = _HISTORY_HEADER_RE.match(line)
        if m:
            if current:
                entries.append(current)
            header = m.group(1).strip()
            ts_match = _HISTORY_TS_RE.search(header)
            current = {
                "ts": ts_match.group(1) if ts_match else None,
                "header": header,
                "body": "",
            }
            continue
        if current is not None:
            current["body"] += line + "\n"
    if current:
        entries.append(current)
    return entries


def _bucket_artifacts_by_phase(
    thread: list[dict], checkpoints: list[dict]
) -> list[tuple[str, str | None, str | None, list[dict]]]:
    """Bucket every artifact into the phase-window in which it was created.

    Returns a list of (phase, start_ts, end_ts, artifacts). Each window
    starts at the previous phase's `completed_at` (or None for the first)
    and ends at this phase's `completed_at`. A trailing in-progress phase
    (artifacts after the last checkpoint) is included as a window with
    `end_ts=None` and a synthetic phase name `"in-progress"`.
    """
    cps = sorted(checkpoints, key=lambda c: c.get("completed_at") or "")
    windows: list[tuple[str, str | None, str | None, list[dict]]] = []
    prev_end: str | None = None
    for cp in cps:
        end = cp.get("completed_at")
        arts = [
            r
            for r in thread
            if (
                (prev_end is None or (r.get("created_at") or "") > prev_end)
                and (end is None or (r.get("created_at") or "") <= end)
            )
        ]
        windows.append((cp.get("phase", "?"), prev_end, end, arts))
        prev_end = end
    # In-progress tail: artifacts created after the last checkpoint
    if prev_end is not None:
        tail = [r for r in thread if (r.get("created_at") or "") > prev_end]
        if tail:
            windows.append(("in-progress", prev_end, None, tail))
    elif not cps and thread:
        # Project has artifacts but no checkpoints yet (e.g. seed in flight)
        windows.append(("in-progress", None, None, list(thread)))
    return windows


def _by_type(arts: list[dict], t: str) -> list[dict]:
    return [a for a in arts if a.get("type") == t]


def _earliest_ts(arts: list[dict]) -> str:
    """Earliest `created_at` across a list of artifacts; "" if none."""
    return min((a.get("created_at") or "" for a in arts), default="")


def _ts(a: dict) -> str:
    return a.get("created_at") or ""


def _phase_narrative(phase: str, arts: list[dict], thread: list[dict]) -> list[dict]:
    """Turn a phase's artifacts into one or more human-readable lines.

    Returns a list of `{kind, text, ids}` dicts (no timestamp; the caller
    fills that in from the phase window). Aggregates routine artifacts
    (HYPs, LITs, Citations, DraftSections) into single summary lines, and
    breaks out individually-interesting events (Critiques, ExperimentResult
    pass/fail/crash, Reviews) so the reader sees what mattered.
    """
    out: list[dict] = []

    if phase == "seed":
        for idea in _by_type(arts, "Idea"):
            summary = (idea.get("summary") or "").strip()
            out.append(
                {
                    "kind": "seed",
                    "ts": _ts(idea),
                    "text": f'Started with idea: "{summary[:160]}"',
                    "ids": [idea["id"]],
                }
            )
        return out

    if phase in ("expand", "gap-fill"):
        hyps = _by_type(arts, "Hypothesis")
        if hyps:
            wild_count = sum(
                1
                for h in hyps
                if "W1" in (h.get("wildness_tickets") or h.get("wildness_ticket") or "")
            )
            verb = "Came up with" if phase == "expand" else "Added"
            noun = "hypothesis" if len(hyps) == 1 else "hypotheses"
            tail = (
                f" ({wild_count} cross-domain transplant{'s' if wild_count != 1 else ''})"
                if wild_count
                else ""
            )
            out.append(
                {
                    "kind": "hypotheses",
                    "ts": _earliest_ts(hyps),
                    "text": f"{verb} {len(hyps)} {noun}{tail}",
                    "ids": [h["id"] for h in hyps],
                }
            )
        return out

    if phase == "survey":
        lits = _by_type(arts, "LitFinding")
        if lits:
            out.append(
                {
                    "kind": "papers",
                    "ts": _earliest_ts(lits),
                    "text": f"Looked up {len(lits)} paper{'s' if len(lits) != 1 else ''} from the literature",
                    "ids": [a["id"] for a in lits],
                }
            )
        return out

    if phase == "screen":
        # Per-HYP boredom kills + novelty verifications
        boredom_kills = [
            c
            for c in _by_type(arts, "Critique")
            if c.get("mode") == "boredom" and c.get("severity") == "high"
        ]
        for c in boredom_kills:
            target = c.get("target_id") or "?"
            concerns = c.get("concerns") or []
            if isinstance(concerns, str):
                concerns = [concerns]
            head = (concerns[0] if concerns else c.get("summary") or "").strip()
            out.append(
                {
                    "kind": "parked",
                    "ts": _ts(c),
                    "text": f"Parked {target} (too boring): {head[:140]}",
                    "ids": [c["id"], target],
                }
            )
        cites = _by_type(arts, "Citation")
        verified = sum(1 for c in cites if c.get("verified"))
        collisions = [
            c
            for c in _by_type(arts, "Critique")
            if c.get("mode") == "novelty" or "novelty" in (c.get("summary") or "").lower()
        ]
        if cites:
            out.append(
                {
                    "kind": "novelty",
                    "ts": _earliest_ts(cites),
                    "text": (
                        f"Verified {verified} of {len(cites)} citations against the literature"
                        + (
                            f" — {len(collisions)} collision{'s' if len(collisions) != 1 else ''} found"
                            if collisions
                            else " (no collisions)"
                        )
                    ),
                    "ids": [c["id"] for c in cites],
                }
            )
        return out

    if phase == "thought-experiment":
        tes = _by_type(arts, "ThoughtExperiment")
        if tes:
            counts = {"promising": 0, "inconclusive": 0, "refuted": 0}
            for te in tes:
                v = (te.get("verdict") or "").strip().lower()
                if v in counts:
                    counts[v] += 1
            bits = [f"{n} {v}" for v, n in counts.items() if n]
            tail = f" ({', '.join(bits)})" if bits else ""
            noun = "toy-problem thought experiment" + ("s" if len(tes) != 1 else "")
            out.append(
                {
                    "kind": "thought-experiment",
                    "ts": _earliest_ts(tes),
                    "text": f"Rolled out {len(tes)} {noun}{tail}",
                    "ids": [t["id"] for t in tes],
                }
            )
            for te in tes:
                if (te.get("verdict") or "").strip().lower() != "refuted":
                    continue
                hid = te.get("hypothesis_id") or "?"
                why = (te.get("predicted_outcome") or te.get("summary") or "").strip()
                out.append(
                    {
                        "kind": "parked",
                        "ts": _ts(te),
                        "text": f"Refuted {hid} on a toy problem (parked): {why[:140]}",
                        "ids": [te["id"], hid],
                    }
                )
        return out

    if phase == "design":
        plans = [p for p in _by_type(arts, "ExperimentPlan") if not p.get("is_ablation")]
        if plans:
            out.append(
                {
                    "kind": "design",
                    "ts": _earliest_ts(plans),
                    "text": f"Designed {len(plans)} experiment{'s' if len(plans) != 1 else ''}",
                    "ids": [p["id"] for p in plans],
                }
            )
        return out

    if phase == "run":
        results = _by_type(arts, "ExperimentResult")
        for r in results:
            status = r.get("status") or "?"
            plan_id = r.get("plan_id") or "?"
            notes = (r.get("notes") or r.get("summary") or "").strip()
            marker = {
                "pass": ("✓", "Experiment passed"),
                "fail": ("✗", "Experiment failed"),
                "crash": ("⚠", "Experiment crashed"),
            }.get(status, ("?", f"Experiment status={status}"))
            tail = f" — {notes[:140]}" if notes else ""
            out.append(
                {
                    "kind": f"result_{status}",
                    "ts": _ts(r),
                    "text": f"{marker[0]} {marker[1]} for {plan_id}{tail}",
                    "ids": [r["id"], plan_id],
                }
            )
        # Ablations spawned during this phase
        ablations = [p for p in _by_type(arts, "ExperimentPlan") if p.get("is_ablation")]
        if ablations:
            out.append(
                {
                    "kind": "ablation",
                    "ts": _earliest_ts(ablations),
                    "text": f"Spawned {len(ablations)} auto-ablation{'s' if len(ablations) != 1 else ''} to verify the proposed mechanism",
                    "ids": [p["id"] for p in ablations],
                }
            )
        return out

    if phase == "critique":
        validity = [c for c in _by_type(arts, "Critique") if c.get("mode") == "validity"]
        for c in validity:
            target = c.get("target_id") or "?"
            sev = c.get("severity") or "?"
            concerns = c.get("concerns") or []
            if isinstance(concerns, str):
                concerns = [concerns]
            head = (concerns[0] if concerns else c.get("summary") or "").strip()
            out.append(
                {
                    "kind": "validity",
                    "ts": _ts(c),
                    "text": f"Validity concern on {target} ({sev}): {head[:160]}",
                    "ids": [c["id"], target],
                }
            )
        return out

    if phase == "write":
        sections = _by_type(arts, "DraftSection")
        if sections:
            names = [s.get("section") or "?" for s in sections]
            out.append(
                {
                    "kind": "write",
                    "ts": _earliest_ts(sections),
                    "text": f"Wrote {len(sections)} section{'s' if len(sections) != 1 else ''}: {', '.join(names)}",
                    "ids": [s["id"] for s in sections],
                }
            )
        return out

    if phase == "final":
        # phase_final emits no artifacts; surface a single line at the
        # phase's end ts (set by the caller from the checkpoint).
        out.append(
            {
                "kind": "final",
                "text": "Assembled and polished `paper-vFINAL.md`",
                "ids": [],
            }
        )
        return out

    if phase == "review":
        reviews = _by_type(arts, "Review")
        for r in reviews:
            persona = r.get("persona") or "?"
            rec = r.get("recommendation") or "?"
            tp = r.get("target_phase") or ""
            sm = (r.get("summary") or "").strip()
            marker = {
                "accept": "✓",
                "minor_revision": "~",
                "major_revision": "✗",
            }.get(rec, "?")
            tail = f" — wants `{tp}`" if rec == "major_revision" and tp else ""
            note = f": {sm[:160]}" if sm else ""
            out.append(
                {
                    "kind": f"review_{rec}",
                    "ts": _ts(r),
                    "text": f"{marker} {persona} → {rec.replace('_', ' ')}{tail}{note}",
                    "ids": [r["id"]],
                }
            )
        return out

    if phase == "in-progress":
        # Render whatever showed up; useful when the dashboard refreshes mid-phase.
        for a in arts:
            t = a.get("type") or "?"
            sm = (a.get("summary") or "").strip()
            out.append(
                {
                    "kind": "pending",
                    "ts": _ts(a),
                    "text": f"({t}) {sm[:160]}",
                    "ids": [a.get("id")] if a.get("id") else [],
                }
            )
        return out

    return out


def project_narrative(pid: str) -> list[dict]:
    """Build a chronologically ordered, human-readable narrative of the project.

    Synthesizes:
      - phase boundaries from `thread/checkpoints/<phase>.json`
      - per-phase artifact summaries (aggregated for routine items, broken
        out for individually-interesting ones)
      - groomed loopback entries from `thread/history.md`

    Returned events have shape:
      { "ts": <iso8601 string>, "phase": <phase or "loopback">,
        "kind": <short tag>, "text": <plain-English line>, "ids": [...] }

    Sorted oldest → newest. Designed to feed a "Story" panel in the dashboard.
    """
    events: list[dict] = []
    thread = _load_full_thread(pid)
    cps = list_checkpoints(pid)
    windows = _bucket_artifacts_by_phase(thread, cps)

    for phase, _start, end, arts in windows:
        for ev in _phase_narrative(phase, arts, thread):
            # If the per-phase synthesizer set its own `ts` (from an
            # artifact's created_at) keep it; otherwise fall back to the
            # phase's end timestamp from its checkpoint.
            ev_ts = ev.get("ts") or end or ""
            events.append({"phase": phase, **ev, "ts": ev_ts})

    # Loopback narrative entries (already groomed prose).
    h_path = history_log(pid)
    if h_path.exists():
        for entry in _parse_history_md_entries(h_path.read_text()):
            header = entry["header"]
            body = entry["body"].strip()
            # Pull the first non-blank body line as a one-liner summary
            summary_line = next(
                (ln.strip() for ln in body.splitlines() if ln.strip()),
                "",
            )
            events.append(
                {
                    "ts": entry["ts"] or "",
                    "phase": "loopback",
                    "kind": "loopback",
                    "text": header,
                    "body": body,
                    "summary": summary_line[:240],
                    "ids": [],
                }
            )

    events.sort(key=lambda e: (e.get("ts") or "", e.get("kind") or ""))
    return events


def active_work(pid: str) -> dict:
    """Compute what's still 'alive' — Hypotheses not parked by screen/critique
    and ExperimentPlans whose latest result isn't terminal (pass/fail or
    crash-with-retries-exhausted). Used by the dashboard's Active Work panel."""
    thread = _load_full_thread(pid)
    by_type = lambda t: [r for r in thread if r.get("type") == t]

    hyps = by_type("Hypothesis")
    plans = by_type("ExperimentPlan")
    results = by_type("ExperimentResult")
    crits = by_type("Critique")

    # Parked = high-severity boredom or validity critique
    parked: set[str] = set()
    for c in crits:
        if c.get("severity") == "high" and c.get("mode") in ("boredom", "validity"):
            t = c.get("target_id", "") or ""
            if t.startswith("HYP-"):
                parked.add(t)

    # Plan -> [parent HYP-* ids]
    hyp_for_plan: dict[str, str] = {}
    plans_for_hyp: dict[str, list[str]] = {}
    for p in plans:
        hyp = next((q for q in (p.get("parent_ids") or []) if q.startswith("HYP-")), None)
        if hyp:
            hyp_for_plan[p["id"]] = hyp
            plans_for_hyp.setdefault(hyp, []).append(p["id"])

    # Latest result per plan (last in chronological order wins)
    latest_for_plan: dict[str, dict] = {}
    for r in results:
        pid_ = r.get("plan_id")
        if pid_:
            latest_for_plan[pid_] = r

    cy = read_cycles(pid)
    crash_retries = cy.get("crash_retries") or {}
    max_crash = int(os.environ.get("AUTOLAB_MAX_CRASH_RETRIES", "2"))

    def plan_status(plan_id: str) -> str:
        latest = latest_for_plan.get(plan_id)
        if not latest:
            return "pending run"
        s = (latest.get("status") or "").lower()
        if s == "crash":
            used = crash_retries.get(plan_id, 0)
            if used >= max_crash:
                return f"crash · retries {used}/{max_crash} exhausted"
            return f"crash · retry {used}/{max_crash}"
        return s or "?"

    def is_terminal(plan_id: str) -> bool:
        latest = latest_for_plan.get(plan_id)
        if not latest:
            return False
        s = (latest.get("status") or "").lower()
        if s in ("pass", "fail"):
            return True
        if s == "crash" and crash_retries.get(plan_id, 0) >= max_crash:
            return True
        return False

    alive_hyps = []
    for h in hyps:
        if h["id"] in parked:
            continue
        plan_ids = plans_for_hyp.get(h["id"], [])
        if not plan_ids:
            status = "pending design"
        else:
            status = " · ".join(plan_status(pid_) for pid_ in plan_ids)
        alive_hyps.append(
            {
                "id": h["id"],
                "claim": (h.get("claim") or h.get("summary") or "")[:240],
                "prediction_metric": h.get("prediction_metric", "") or "",
                "prediction_threshold": h.get("prediction_threshold"),
                "prediction_direction": h.get("prediction_direction", "") or "",
                "wildness": h.get("wildness_tickets") or h.get("wildness_ticket") or "",
                "plan_ids": plan_ids,
                "status": status,
            }
        )

    active_plans = []
    for p in plans:
        if is_terminal(p["id"]):
            continue
        active_plans.append(
            {
                "id": p["id"],
                "summary": (p.get("summary") or "")[:240],
                "is_ablation": bool(p.get("is_ablation")),
                "compute_budget_minutes": p.get("compute_budget_minutes"),
                "seeds": p.get("seeds") or [],
                "status": plan_status(p["id"]),
                "hyp_id": hyp_for_plan.get(p["id"]),
            }
        )

    return {"hypotheses": alive_hyps, "plans": active_plans}


def project_detail(pid: str) -> dict:
    return {
        **project_summary(pid),
        "checkpoints": list_checkpoints(pid),
        "ledger": parse_ledger(cost_ledger(pid)),
        "thoughts": list_thoughts(pid),
        "drafts": list_drafts(pid),
        "experiments": list_experiments(pid),
        "parking_lot": safe_read(parking_lot(pid), 30_000),
        "papers_index": safe_read(papers_index(pid), 30_000),
        "live": live_status(pid),
        "thread_events": parse_thread_events(pid, 100),
        "narrative": project_narrative(pid),
        "active": active_work(pid),
    }


def read_thought_full(pid: str, thought_id: str) -> dict:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", thought_id)
    if not safe_id:
        return {"error": "bad_id"}
    p = thoughts_dir(pid) / f"{safe_id}.md"
    if not p.exists():
        return {"error": "not_found", "id": safe_id}
    return {"id": safe_id, "content": safe_read(p, 200_000)}


_BINARY_DRAFT_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip"}


def _safe_draft_name(name: str) -> str | None:
    safe = re.sub(r"[^A-Za-z0-9._-]", "", name)
    if not safe or safe.startswith(".") or "/" in safe or "\\" in safe:
        return None
    return safe


def read_draft_full(pid: str, filename: str) -> dict:
    safe = _safe_draft_name(filename)
    if not safe:
        return {"error": "bad_name"}
    p = drafts_dir(pid) / safe
    if not p.exists() or not p.is_file():
        return {"error": "not_found", "name": safe}
    suffix = p.suffix.lower()
    if suffix in _BINARY_DRAFT_EXTS:
        return {
            "name": safe,
            "binary": True,
            "size": p.stat().st_size,
            "raw_url": f"/raw/{pid}/draft/{safe}",
        }
    return {"name": safe, "content": safe_read(p, 500_000)}


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _raw(self, p: Path, content_type: str = "application/octet-stream"):
        body = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'inline; filename="{p.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        try:
            if path == "/" or path == "/index.html":
                if not STATIC_INDEX.exists():
                    return self._html(f"<h1>500</h1><p>missing {STATIC_INDEX}</p>")
                return self._html(STATIC_INDEX.read_text(encoding="utf-8"))
            if path == "/api/projects":
                projects = [project_summary(p) for p in list_projects()]
                projects.sort(key=lambda x: x.get("last_activity_ts") or 0, reverse=True)
                return self._json(
                    {"projects": projects, "now": datetime.now(UTC).isoformat(timespec="seconds")}
                )
            if path.startswith("/raw/"):
                rest = path[len("/raw/") :]
                parts = rest.split("/", 3)
                if len(parts) < 3 or parts[1] != "draft":
                    return self.send_error(404, "Not Found")
                pid, _, name = parts[0], parts[1], parts[2]
                if pid not in list_projects():
                    return self.send_error(404, "Not Found")
                safe = _safe_draft_name(name)
                if not safe:
                    return self.send_error(400, "Bad name")
                p = drafts_dir(pid) / safe
                if not p.exists() or not p.is_file():
                    return self.send_error(404, "Not Found")
                ct = {
                    ".pdf": "application/pdf",
                    ".md": "text/markdown; charset=utf-8",
                    ".bib": "text/plain; charset=utf-8",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                }.get(p.suffix.lower(), "application/octet-stream")
                return self._raw(p, ct)
            if path.startswith("/api/project/"):
                rest = path[len("/api/project/") :]
                parts = rest.split("/", 2)
                pid = parts[0]
                if pid not in list_projects():
                    return self._json({"error": "not_found", "id": pid}, code=404)
                if len(parts) == 1:
                    return self._json(project_detail(pid))
                if len(parts) >= 2 and parts[1] == "thought":
                    if len(parts) < 3 or not parts[2]:
                        return self._json({"error": "missing_id"}, code=400)
                    return self._json(read_thought_full(pid, parts[2]))
                if len(parts) >= 2 and parts[1] == "draft":
                    if len(parts) < 3 or not parts[2]:
                        return self._json({"error": "missing_name"}, code=400)
                    return self._json(read_draft_full(pid, parts[2]))
                return self._json({"error": "unknown_subpath"}, code=404)
            self.send_error(404, "Not Found")
        except Exception as e:
            self._json({"error": str(e)}, code=500)

    def log_message(self, fmt, *args):
        pass  # quiet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"autolab dashboard → http://{args.host}:{args.port}")
    print("Ctrl-C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
