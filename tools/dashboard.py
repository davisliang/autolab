#!/usr/bin/env python3
"""autolab progress dashboard.

Single-file stdlib HTTP server that reads directly from `projects/<id>/` and
renders a live-refreshing web view of every run's progress.

Usage:
    uv run python tools/dashboard.py            # http://localhost:8765
    uv run python tools/dashboard.py --port 9000
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from _paths import (
    PROJECTS,
    checkpoints_dir,
    cost_ledger,
    drafts_dir,
    experiments_dir,
    list_projects,
    orchestrator_log,
    papers_index,
    parking_lot,
    project_dir,
    thoughts_dir,
    thread_log,
)

PHASES = [
    "seed", "expand", "survey", "gap-fill", "screen",
    "design", "run", "critique", "write", "final",
]


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
        "calls": 0, "fresh_in": 0, "cache_create": 0,
        "cache_read": 0, "in_tokens": 0, "out_tokens": 0,
    }
    if not p.exists():
        return {
            "rows": [],
            "total_fresh_in": 0, "total_cache_create": 0, "total_cache_read": 0,
            "total_in_tokens": 0, "total_out_tokens": 0,
            "cache_hit_ratio": 0.0,
            "by_phase": {}, "by_model": {},
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
                    fresh = int(parts[4]); cc = int(parts[5]); cr = int(parts[6]); out = int(parts[7])
                else:
                    # 6 or 7 col legacy: column 4 already holds total input, no cache split
                    fresh = int(parts[4]); cc = 0; cr = 0; out = int(parts[5])
            except ValueError:
                continue
            in_total = fresh + cc + cr
            rows.append({
                "ts": ts, "phase": phase, "skill": skill, "model": model,
                "fresh_in": fresh, "cache_create": cc, "cache_read": cr,
                "input_tokens": in_total, "output_tokens": out,
            })
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
        out.append({
            "phase": data.get("phase", f.stem),
            "completed_artifact_ids": data.get("completed_artifact_ids", []),
            "next_action": data.get("next_action"),
            "completed_at": data.get("completed_at"),
        })
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
        body = text[m.end():].strip()
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
    return {"id": p.stem, "title": title, "summary": summary, "mtime": mtime, "path": str(p.relative_to(PROJECTS.parent))}


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
        out.append({
            "name": p.name,
            "size": st.st_size,
            "mtime": st.st_mtime,
        })
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
            inflight_calls.append({
                "phase": m.group(1), "skill": m.group(2), "model": m.group(3),
                "started_at": ts,
            })
            continue
        m = _LOG_CALL_EXIT_RE.search(line) or _LOG_CALL_TIMEOUT_RE.search(line)
        if m:
            ph, sk = (m.group(2), m.group(3)) if m.re is _LOG_CALL_EXIT_RE else (m.group(1), m.group(2))
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
            out.append({
                "id": ev.get("id"),
                "type": ev.get("type"),
                "author": ev.get("author"),
                "summary": (ev.get("summary") or "")[:240],
                "ts": ev.get("ts") or ev.get("created_at"),
                "parent_ids": ev.get("parent_ids") or [],
            })
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
        "total_in_tokens": ledger["total_in_tokens"],
        "total_out_tokens": ledger["total_out_tokens"],
        "n_calls": sum(v["calls"] for v in ledger["by_phase"].values()),
        "last_activity_ts": last_log_ts,
        "cycle": cy.get("current", 1),
        "n_retreats": len(cy.get("history", [])),
    }


def project_detail(pid: str, log_lines: int = 400) -> dict:
    return {
        **project_summary(pid),
        "checkpoints": list_checkpoints(pid),
        "ledger": parse_ledger(cost_ledger(pid)),
        "recent_log": tail_lines(orchestrator_log(pid), log_lines),
        "thoughts": list_thoughts(pid),
        "drafts": list_drafts(pid),
        "experiments": list_experiments(pid),
        "parking_lot": safe_read(parking_lot(pid), 30_000),
        "papers_index": safe_read(papers_index(pid), 30_000),
        "live": live_status(pid),
        "thread_events": parse_thread_events(pid, 100),
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


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>autolab dashboard</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { background:#0e1116; color:#cfd6e4; font:13px/1.45 -apple-system,BlinkMacSystemFont,system-ui,sans-serif; margin:0; }
  header { padding:10px 18px; background:#161b22; border-bottom:1px solid #2a313c; display:flex; align-items:center; gap:14px; }
  header h1 { font-size:14px; margin:0; color:#7dd3fc; font-weight:600; letter-spacing:.5px; }
  header .meta { color:#8b95a7; font-size:12px; }
  main { display:grid; grid-template-columns: 300px 1fr; height: calc(100vh - 41px); }
  #projects { border-right:1px solid #2a313c; padding:10px; overflow-y:auto; }
  #detail { padding:14px 22px; overflow-y:auto; }
  .proj { padding:8px 10px; border-radius:6px; cursor:pointer; margin-bottom:4px; }
  .proj:hover { background:#1a2030; }
  .proj.active { background:#1d2742; border:1px solid #2f3e63; }
  .proj .id { font-weight:600; color:#dde3ef; word-break: break-all; font-size:12px; }
  .proj .sub { font-size:11px; color:#7c8699; margin-top:2px; }
  .phases { display:flex; gap:4px; margin:14px 0; flex-wrap:wrap; }
  .phase { padding:4px 10px; border-radius:14px; background:#1a2030; color:#7c8699; font-size:11px; border:1px solid #2a313c; }
  .phase.done { background:#143123; color:#86efac; border-color:#1e5235; }
  .phase.active { background:#3a2a14; color:#fbbf24; border-color:#7a5018; animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.5; } }
  h2 { font-size:13px; color:#7dd3fc; margin:18px 0 8px; text-transform:uppercase; letter-spacing:.5px; font-weight:600; }
  h2 .ctl { float:right; font-size:11px; color:#8b95a7; font-weight:400; text-transform:none; letter-spacing:0; cursor:pointer; }
  h2 .ctl:hover { color:#7dd3fc; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .card { background:#161b22; border:1px solid #2a313c; border-radius:6px; padding:10px 12px; }
  .stat { font-size:18px; color:#dde3ef; }
  .stat .lbl { font-size:11px; color:#7c8699; text-transform:uppercase; letter-spacing:.5px; }
  /* Default scrollable boxes */
  pre { background:#0a0e14; border:1px solid #2a313c; border-radius:4px; padding:10px; overflow:auto; max-height:360px; white-space:pre-wrap; word-break:break-word; font:11px/1.5 ui-monospace,Menlo,monospace; color:#bdc4d3; margin:0; }
  pre.tall { max-height:540px; }
  pre.short { max-height:240px; }
  .scrollbox { max-height:420px; overflow-y:auto; padding-right:4px; }
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th, td { text-align:left; padding:4px 8px; border-bottom:1px solid #1d242e; }
  th { color:#7c8699; font-weight:500; font-size:11px; text-transform:uppercase; }
  /* Thought card: clickable, expandable */
  .thought { background:#161b22; border:1px solid #2a313c; border-radius:6px; padding:8px 10px; margin-bottom:6px; cursor:pointer; transition:background .12s; }
  .thought:hover { background:#1a2030; border-color:#3a4658; }
  .thought .id { color:#7dd3fc; font-weight:600; font-size:11px; font-family:ui-monospace,Menlo,monospace; }
  .thought .title { color:#dde3ef; margin-top:2px; font-weight:500; }
  .thought .sum { color:#8b95a7; font-size:11px; margin-top:3px; line-height:1.5; }
  .thought.expanded { background:#1a2030; border-color:#3a4658; }
  .thought.expanded .sum { display:none; }
  .thought-full { margin-top:8px; max-height:420px; overflow-y:auto; background:#0a0e14; border:1px solid #2a313c; border-radius:4px; padding:10px; font:11px/1.55 ui-monospace,Menlo,monospace; color:#bdc4d3; white-space:pre-wrap; word-break:break-word; }
  .thought-full.loading { color:#5b667a; font-style:italic; }
  /* Thread event row */
  .ev { padding:5px 8px; border-bottom:1px solid #1d242e; display:grid; grid-template-columns: 70px 64px 1fr; gap:8px; align-items:start; font-size:11px; }
  .ev:last-child { border-bottom:none; }
  .ev .ts { color:#5b667a; font-family:ui-monospace,Menlo,monospace; }
  .ev .id { color:#7dd3fc; font-family:ui-monospace,Menlo,monospace; font-weight:600; }
  .ev .body { color:#bdc4d3; }
  .ev .body .type { color:#fbbf24; font-weight:600; margin-right:4px; }
  .ev .body .author { color:#8b95a7; font-size:10px; }
  /* Token histogram */
  .hist { display:flex; flex-direction:column; gap:8px; padding:4px 0; }
  .hrow { display:grid; grid-template-columns: 80px 1fr; gap:10px; align-items:center; }
  .hlbl { color:#7c8699; font-size:11px; text-transform:uppercase; letter-spacing:.5px; font-weight:500; }
  .hbars { display:flex; flex-direction:column; gap:3px; }
  .hpair { display:grid; grid-template-columns: 1fr 180px; gap:8px; align-items:center; }
  .htrack { background:#0a0e14; border-radius:2px; height:12px; overflow:hidden; display:flex; }
  .hbar { height:100%; min-width:0; transition: width .25s; }
  .hbar.fresh  { background: #f97316; }            /* orange = uncached input */
  .hbar.create { background: #facc15; }            /* yellow = cache write   */
  .hbar.read   { background: linear-gradient(90deg,#1e5235,#86efac); } /* green = cache hit */
  .hbar.out    { background: linear-gradient(90deg,#1c3a5c,#7dd3fc); }
  .hcnt { font-size:10px; color:#8b95a7; font-family:ui-monospace,Menlo,monospace; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .hcnt .tag { display:inline-block; width:24px; color:#5b667a; }
  .legend { display:flex; gap:14px; font-size:10px; color:#8b95a7; padding:0 0 6px 90px; }
  .legend .swatch { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }
  /* Live status banner — single-line, expandable */
  .live-banner { background:linear-gradient(90deg,#1d2742,#161b22); border:1px solid #2f3e63; border-radius:6px; padding:8px 12px; margin-bottom:14px; user-select:none; }
  .live-banner.idle { background:#161b22; border-color:#2a313c; }
  .live-banner.expandable { cursor:pointer; }
  .live-banner.expandable:hover { background:linear-gradient(90deg,#243154,#1a2030); }
  .live-banner .banner-row { color:#fbbf24; font-weight:500; font-size:12px; display:flex; justify-content:space-between; align-items:center; gap:10px; }
  .live-banner.idle .banner-row { color:#8b95a7; font-weight:400; }
  .live-banner .expand-hint { color:#5b667a; font-size:10px; font-weight:400; }
  .live-banner .banner-detail { display:none; margin-top:8px; flex-direction:column; gap:4px; }
  .live-banner.open .banner-detail { display:flex; }
  .live-banner .call { display:flex; gap:10px; font-size:11px; padding:4px 8px; background:#0a0e14; border-radius:4px; }
  .live-banner .call .skill { color:#7dd3fc; font-weight:600; min-width:140px; }
  .live-banner .call .model { color:#86efac; }
  .live-banner .call .age { color:#8b95a7; margin-left:auto; }
  /* One-line stat strip in place of cards */
  .statstrip { padding:10px 12px; background:#161b22; border:1px solid #2a313c; border-radius:6px; color:#dde3ef; font-size:13px; display:flex; gap:18px; align-items:center; flex-wrap:wrap; margin-bottom:4px; }
  .statstrip .item b { color:#7dd3fc; font-weight:600; font-variant-numeric:tabular-nums; }
  .statstrip .item .lbl { color:#7c8699; font-size:11px; text-transform:uppercase; letter-spacing:.5px; margin-left:6px; }
  .statstrip .sep { color:#3a4658; }
  /* Collapsible H2: parking lot, papers index, etc. */
  h2.collapsible { cursor:pointer; user-select:none; }
  h2.collapsible:hover { color:#bae6fd; }
  h2.collapsible .caret { display:inline-block; width:14px; color:#5b667a; font-weight:400; }
  .empty { color:#5b667a; font-style:italic; padding:6px 0; }
  .status { display:inline-block; width:8px; height:8px; border-radius:50%; background:#5b667a; margin-right:6px; }
  .status.live { background:#86efac; box-shadow:0 0 6px #86efac; }
  .status.stale { background:#fbbf24; }
  .toggle { font-size:11px; color:#7dd3fc; cursor:pointer; user-select:none; }
  .toggle input { vertical-align:middle; margin-right:4px; }
</style>
</head>
<body>
<header>
  <h1>autolab</h1>
  <span class="meta" id="updated">—</span>
  <label class="toggle"><input type="checkbox" id="follow" checked> follow tail</label>
  <label class="toggle"><input type="checkbox" id="autorefresh" checked> auto-refresh 3s</label>
</header>
<main>
  <aside id="projects"><div class="empty">loading…</div></aside>
  <section id="detail"><div class="empty">select a project</div></section>
</main>
<script>
let activeId = null;
const expandedThoughts = new Map(); // id -> content
let timer = null;
function fmtTok(x){ return (x||0).toLocaleString(); }
function escHtml(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function fmtAgo(ts){
  if (!ts) return '—';
  let s;
  if (typeof ts === 'string') s = Math.floor((Date.now() - new Date(ts).getTime())/1000);
  else s = Math.floor(Date.now()/1000 - ts);
  if (!isFinite(s) || s < 0) return '—';
  if (s < 60) return s + 's ago';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  if (s < 86400) return Math.floor(s/3600) + 'h ago';
  return Math.floor(s/86400) + 'd ago';
}
function liveDot(ts){
  if (!ts) return '<span class="status"></span>';
  const s = Date.now()/1000 - ts;
  if (s < 120) return '<span class="status live"></span>';
  if (s < 1800) return '<span class="status stale"></span>';
  return '<span class="status"></span>';
}
async function loadProjects(){
  const r = await fetch('/api/projects'); const data = await r.json();
  const el = document.getElementById('projects');
  if (!data.projects.length){ el.innerHTML = '<div class="empty">no projects yet — run ./start --idea "..."</div>'; return; }
  el.innerHTML = data.projects.map(p => `
    <div class="proj ${p.id===activeId?'active':''}" data-id="${p.id}">
      <div class="id">${liveDot(p.last_activity_ts)}${escHtml(p.id)}</div>
      <div class="sub">${escHtml(p.current_phase||'—')} · ${fmtTok((p.total_in_tokens||0)+(p.total_out_tokens||0))} tok · ${p.n_calls} calls · ${fmtAgo(p.last_activity_ts)}</div>
    </div>`).join('');
  el.querySelectorAll('.proj').forEach(d => d.addEventListener('click', () => {
    if (activeId !== d.dataset.id){ activeId = d.dataset.id; expandedThoughts.clear(); }
    loadDetail(); loadProjects();
  }));
  if (!activeId && data.projects.length){ activeId = data.projects[0].id; loadDetail(); loadProjects(); }
}
// Persisted across re-renders: whether the live banner detail is open
let bannerOpen = false;
function liveBanner(live, cycle, nRetreats){
  const running = live.running_phase;
  const idle = !running && live.inflight_calls.length === 0;
  const callsCount = live.inflight_calls.length;
  const cycleStr = cycle && cycle > 1
    ? ` · cycle ${cycle}` + (nRetreats ? ` (${nRetreats} retreat${nRetreats>1?'s':''})` : '')
    : '';
  const callsStr = callsCount ? ` · ${callsCount} call${callsCount>1?'s':''} in flight` : '';
  const phaseAgo = live.phase_started_at ? ` · started ${fmtAgo(live.phase_started_at)}` : '';
  const lastLog = live.last_event_ts ? ` · last log ${fmtAgo(live.last_event_ts)}` : '';
  const summary = running
    ? `▶ ${escHtml(running)}${cycleStr}${callsStr}${phaseAgo}`
    : `◼ idle${cycleStr}${lastLog}`;
  const expandable = callsCount > 0;
  const detail = expandable
    ? '<div class="banner-detail">' + live.inflight_calls.map(c =>
        `<div class="call"><span class="skill">${escHtml(c.skill)}</span> <span>phase=${escHtml(c.phase)}</span> <span class="model">${escHtml(c.model)}</span> <span class="age">started ${fmtAgo(c.started_at)}</span></div>`
      ).join('') + '</div>'
    : '';
  const cls = (idle?'idle ':'') + (expandable?'expandable ':'') + (expandable && bannerOpen ? 'open':'');
  const hint = expandable ? `<span class="expand-hint">${bannerOpen?'▾':'▸'} ${callsCount} call${callsCount>1?'s':''}</span>` : '';
  return `<div class="live-banner ${cls}" id="liveBanner">
    <div class="banner-row">
      <span>${summary}</span>
      ${hint}
    </div>
    ${detail}
  </div>`;
}

// Collapsed sections — track by stable key so state survives re-renders.
const collapsedSections = new Set(['parking', 'papersIndex']); // collapsed by default
function applyCollapsibles(){
  document.querySelectorAll('h2.collapsible').forEach(h => {
    const k = h.dataset.key;
    const target = document.getElementById(k);
    const collapsed = collapsedSections.has(k);
    const caret = h.querySelector('.caret');
    if (caret) caret.textContent = collapsed ? '▸' : '▾';
    if (target) target.style.display = collapsed ? 'none' : '';
    h.onclick = () => {
      if (collapsedSections.has(k)) collapsedSections.delete(k);
      else collapsedSections.add(k);
      applyCollapsibles();
    };
  });
}

// Drafts: click a row to expand its contents inline (text), or open a new tab (binary).
const expandedDrafts = new Map();  // name -> content | '__loading__' | {binary, raw_url, size}
async function loadDraftFull(name){
  if (!activeId) return;
  if (expandedDrafts.has(name)) return;
  expandedDrafts.set(name, '__loading__');
  renderDrafts(window.__lastDetail.drafts);
  const r = await fetch('/api/project/' + encodeURIComponent(activeId) + '/draft/' + encodeURIComponent(name));
  const j = await r.json();
  if (j.binary){
    // binary: open in new tab, don't keep expanded
    expandedDrafts.delete(name);
    window.open(j.raw_url, '_blank', 'noopener');
    renderDrafts(window.__lastDetail.drafts);
    return;
  }
  expandedDrafts.set(name, j.content || j.error || '(empty)');
  renderDrafts(window.__lastDetail.drafts);
}
function renderDrafts(drafts, prevExpandedScroll){
  const wrap = document.getElementById('drafts');
  if (!wrap) return;
  if (!drafts.length){ wrap.innerHTML = '<div class="empty">none yet — paper renders here after the write phase</div>'; return; }
  wrap.innerHTML = drafts.map(f => {
    const exp = expandedDrafts.get(f.name);
    const isExp = expandedDrafts.has(f.name);
    let fullHtml = '';
    if (isExp){
      if (exp === '__loading__') fullHtml = '<div class="thought-full loading">loading…</div>';
      else fullHtml = `<div class="thought-full">${escHtml(exp)}</div>`;
    }
    return `<div class="thought ${isExp?'expanded':''}" data-name="${escHtml(f.name)}">
      <div class="title">${escHtml(f.name)}</div>
      <div class="sum">${(f.size/1024).toFixed(1)} KB · ${fmtAgo(f.mtime)}</div>
      ${fullHtml}
    </div>`;
  }).join('');
  wrap.querySelectorAll('.thought').forEach(el => el.addEventListener('click', (ev) => {
    ev.stopPropagation();
    const name = el.dataset.name;
    if (expandedDrafts.has(name)){ expandedDrafts.delete(name); renderDrafts(drafts); }
    else { loadDraftFull(name); }
  }));
  if (prevExpandedScroll){
    Object.entries(prevExpandedScroll).forEach(([name, top]) => {
      if (top > 4){
        const card = wrap.querySelector('.thought[data-name="' + CSS.escape(name) + '"] .thought-full');
        if (card) card.scrollTop = top;
      }
    });
  }
}
function pctOf(part, total){ return total > 0 ? (part/total*100).toFixed(1) : '0.0'; }
function tokenHistogram(byBucket){
  const keys = Object.keys(byBucket);
  if (!keys.length) return '<div class="empty">no calls yet</div>';
  let max = 0;
  keys.forEach(k => { max = Math.max(max, byBucket[k].in_tokens||0, byBucket[k].out_tokens||0); });
  if (max === 0) max = 1;
  const legend = `<div class="legend">
    <span><span class="swatch" style="background:#f97316"></span>fresh in</span>
    <span><span class="swatch" style="background:#facc15"></span>cache write</span>
    <span><span class="swatch" style="background:linear-gradient(90deg,#1e5235,#86efac)"></span>cache hit</span>
    <span><span class="swatch" style="background:linear-gradient(90deg,#1c3a5c,#7dd3fc)"></span>output</span>
  </div>`;
  const rows = keys.map(k => {
    const v = byBucket[k];
    const fresh = v.fresh_in || 0;
    const cc = v.cache_create || 0;
    const cr = v.cache_read || 0;
    const inTotal = v.in_tokens || (fresh + cc + cr);
    const out = v.out_tokens || 0;
    // Each segment's width is proportional to the global max (so phases are comparable),
    // and segments stack within the input bar.
    const freshPct = (fresh / max * 100).toFixed(2);
    const ccPct    = (cc    / max * 100).toFixed(2);
    const crPct    = (cr    / max * 100).toFixed(2);
    const outPct   = (out   / max * 100).toFixed(2);
    const hitPct = pctOf(cr, inTotal);
    return `<div class="hrow">
      <div class="hlbl">${escHtml(k)}</div>
      <div class="hbars">
        <div class="hpair">
          <div class="htrack">
            <div class="hbar fresh"  style="width:${freshPct}%" title="fresh ${fmtTok(fresh)}"></div>
            <div class="hbar create" style="width:${ccPct}%"    title="cache write ${fmtTok(cc)}"></div>
            <div class="hbar read"   style="width:${crPct}%"    title="cache hit ${fmtTok(cr)}"></div>
          </div>
          <span class="hcnt"><span class="tag">in</span>${fmtTok(inTotal)} · ${hitPct}% hit</span>
        </div>
        <div class="hpair">
          <div class="htrack"><div class="hbar out" style="width:${outPct}%"></div></div>
          <span class="hcnt"><span class="tag">out</span>${fmtTok(out)}</span>
        </div>
      </div>
    </div>`;
  }).join('');
  return legend + '<div class="hist">' + rows + '</div>';
}
function threadEventsHtml(events){
  if (!events.length) return '<div class="empty">no thread events yet</div>';
  return events.map(e => {
    const ts = e.ts ? String(e.ts).slice(11,19) : '';
    return `<div class="ev"><span class="ts">${escHtml(ts)}</span><span class="id">${escHtml(e.id||'')}</span><span class="body"><span class="type">${escHtml(e.type||'')}</span>${escHtml(e.summary||'')} ${e.author?'<span class="author">— '+escHtml(e.author)+'</span>':''}</span></div>`;
  }).join('');
}
async function loadThoughtFull(tid){
  if (!activeId) return;
  if (expandedThoughts.has(tid)) return; // cached
  expandedThoughts.set(tid, '__loading__');
  renderThoughts(window.__lastDetail.thoughts);
  const r = await fetch('/api/project/' + encodeURIComponent(activeId) + '/thought/' + encodeURIComponent(tid));
  const j = await r.json();
  expandedThoughts.set(tid, j.content || j.error || '(empty)');
  renderThoughts(window.__lastDetail.thoughts);
}
function renderThoughts(thoughts, prevExpandedScroll){
  const wrap = document.getElementById('thoughts');
  if (!wrap) return;
  if (!thoughts.length){ wrap.innerHTML = '<div class="empty">none yet</div>'; return; }
  wrap.innerHTML = thoughts.map(t => {
    const exp = expandedThoughts.get(t.id);
    const isExp = expandedThoughts.has(t.id);
    let fullHtml = '';
    if (isExp){
      if (exp === '__loading__') fullHtml = '<div class="thought-full loading">loading…</div>';
      else fullHtml = `<div class="thought-full">${escHtml(exp)}</div>`;
    }
    return `<div class="thought ${isExp?'expanded':''}" data-id="${escHtml(t.id)}">
      <div class="id">${escHtml(t.id)}</div>
      <div class="title">${escHtml(t.title)}</div>
      <div class="sum">${escHtml(t.summary||'')}</div>
      ${fullHtml}
    </div>`;
  }).join('');
  wrap.querySelectorAll('.thought').forEach(el => el.addEventListener('click', (ev) => {
    ev.stopPropagation();
    const tid = el.dataset.id;
    if (expandedThoughts.has(tid)){ expandedThoughts.delete(tid); renderThoughts(thoughts); }
    else { loadThoughtFull(tid); }
  }));
  // Restore scroll on individual expanded thought panes
  if (prevExpandedScroll){
    Object.entries(prevExpandedScroll).forEach(([id, top]) => {
      if (top > 4){
        const card = wrap.querySelector('.thought[data-id="' + CSS.escape(id) + '"] .thought-full');
        if (card) card.scrollTop = top;
      }
    });
  }
}
async function loadDetail(){
  if (!activeId) return;
  const r = await fetch('/api/project/' + encodeURIComponent(activeId) + '?log_lines=400');
  const d = await r.json();
  window.__lastDetail = d;
  const phaseHtml = d.all_phases.map(ph => {
    const done = d.completed_phases.includes(ph);
    const active = ph === d.current_phase && !done;
    return `<span class="phase ${done?'done':''} ${active?'active':''}">${ph}</span>`;
  }).join('');
  const histHtml = tokenHistogram(d.ledger.by_phase);
  const histByModelHtml = tokenHistogram(d.ledger.by_model || {});
  const recentRows = (d.ledger.rows||[]).slice(-15).reverse().map(r => {
    const fresh = r.fresh_in||0, cc = r.cache_create||0, cr = r.cache_read||0;
    const hit = r.input_tokens > 0 ? (cr/r.input_tokens*100).toFixed(0)+'%' : '—';
    return `<tr><td>${escHtml(r.ts.slice(11,19))}</td><td>${escHtml(r.phase)}</td><td>${escHtml(r.skill)}</td><td>${escHtml(r.model)}</td><td>${fmtTok(fresh)}</td><td>${fmtTok(cc)}</td><td>${fmtTok(cr)}</td><td>${hit}</td><td>${fmtTok(r.output_tokens)}</td></tr>`;
  }).join('');
  const experiments = d.experiments.length ? d.experiments.map(e => `<div>${escHtml(e.name)} · ${fmtAgo(e.mtime)}</div>`).join('') : '<div class="empty">none yet</div>';
  const logText = (d.recent_log||[]).join('\\n');
  const detail = document.getElementById('detail');
  // Snapshot scroll positions of inner panes so user reading isn't yanked.
  // Rule: if scrollTop > 4, user has scrolled — preserve. If at top, natural top stays.
  const prevLogScroll = (function(){ const el = document.getElementById('log'); return el ? {top: el.scrollTop, atBottom: el.scrollHeight - el.scrollTop - el.clientHeight < 20} : null; })();
  const prevThoughtsScroll = (function(){ const el = document.getElementById('thoughts'); return el ? el.scrollTop : 0; })();
  const prevThreadScroll = (function(){ const el = document.getElementById('threadEvents'); return el ? el.scrollTop : 0; })();
  const prevExpandedScroll = {};
  document.querySelectorAll('#thoughts .thought-full').forEach(el => {
    const card = el.closest('.thought');
    if (card && card.dataset.id) prevExpandedScroll[card.dataset.id] = el.scrollTop;
  });
  const prevExpandedDraftScroll = {};
  document.querySelectorAll('#drafts .thought-full').forEach(el => {
    const card = el.closest('.thought');
    if (card && card.dataset.name) prevExpandedDraftScroll[card.dataset.name] = el.scrollTop;
  });
  detail.innerHTML = `
    <h2>${escHtml(d.id)}</h2>
    ${liveBanner(d.live, d.cycle, d.n_retreats)}
    <div class="phases">${phaseHtml}</div>
    <div class="statstrip">
      <span class="item"><b>${fmtTok(d.ledger.total_in_tokens)}</b><span class="lbl">in</span></span>
      <span class="sep">·</span>
      <span class="item"><b>${fmtTok(d.ledger.total_out_tokens)}</b><span class="lbl">out</span></span>
      <span class="sep">·</span>
      <span class="item"><b>${(d.ledger.cache_hit_ratio*100).toFixed(1)}%</b><span class="lbl">cache hit</span></span>
      <span class="sep">·</span>
      <span class="item"><b>${d.n_calls}</b><span class="lbl">calls</span></span>
    </div>
    <h2>orchestrator log <span class="ctl">${(d.recent_log||[]).length} lines</span></h2>
    <pre id="log" class="tall">${escHtml(logText)}</pre>
    <h2>thread events <span class="ctl">${(d.thread_events||[]).length} shown</span></h2>
    <div id="threadEvents" class="scrollbox card" style="padding:0">${threadEventsHtml(d.thread_events||[])}</div>
    <div class="grid2">
      <div>
        <h2>thoughts <span class="ctl">${d.thoughts.length} · click to expand</span></h2>
        <div class="scrollbox" id="thoughts"></div>
      </div>
      <div>
        <h2>tokens by phase</h2>
        <div class="scrollbox short">${histHtml}</div>
        <h2>tokens by model</h2>
        <div class="scrollbox short" id="histByModel">${histByModelHtml}</div>
        <h2>recent calls</h2>
        <div class="scrollbox short"><table><thead><tr><th>time</th><th>phase</th><th>skill</th><th>model</th><th>fresh</th><th>cache wr</th><th>cache rd</th><th>hit</th><th>out</th></tr></thead><tbody>${recentRows || '<tr><td colspan=9 class="empty">none</td></tr>'}</tbody></table></div>
      </div>
    </div>
    <div class="grid2">
      <div>
        <h2>drafts <span class="ctl">${d.drafts.length} · click to preview</span></h2>
        <div class="scrollbox short" id="drafts"></div>
      </div>
      <div><h2>experiments</h2><div class="scrollbox short">${experiments}</div></div>
    </div>
    <h2 class="collapsible" data-key="parking"><span class="caret">▸</span> parking lot</h2>
    <pre id="parking">${escHtml(d.parking_lot||'(empty)')}</pre>
    <h2 class="collapsible" data-key="papersIndex"><span class="caret">▸</span> papers index</h2>
    <pre id="papersIndex">${escHtml(d.papers_index||'(empty)')}</pre>
  `;
  renderThoughts(d.thoughts || [], prevExpandedScroll);
  renderDrafts(d.drafts || [], prevExpandedDraftScroll);
  applyCollapsibles();
  // Wire live-banner click-to-expand
  const lb = document.getElementById('liveBanner');
  if (lb && lb.classList.contains('expandable')){
    lb.addEventListener('click', () => {
      bannerOpen = !bannerOpen;
      lb.classList.toggle('open', bannerOpen);
      const hint = lb.querySelector('.expand-hint');
      if (hint) hint.textContent = (bannerOpen ? '▾' : '▸') + hint.textContent.slice(1);
    });
  }
  // Log: follow-tail OR preserve scroll
  const logEl = document.getElementById('log');
  if (logEl){
    if (document.getElementById('follow').checked) logEl.scrollTop = logEl.scrollHeight;
    else if (prevLogScroll) logEl.scrollTop = prevLogScroll.top;
  }
  // Thoughts/thread events: preserve scroll if user moved off the top
  const thoughtsEl = document.getElementById('thoughts');
  if (thoughtsEl && prevThoughtsScroll > 4) thoughtsEl.scrollTop = prevThoughtsScroll;
  const threadEl = document.getElementById('threadEvents');
  if (threadEl && prevThreadScroll > 4) threadEl.scrollTop = prevThreadScroll;
  document.getElementById('updated').textContent = 'updated ' + new Date().toLocaleTimeString();
}
async function tick(){ await loadProjects(); await loadDetail(); }
function startTimer(){ if (timer) return; timer = setInterval(tick, 3000); }
function stopTimer(){ if (timer){ clearInterval(timer); timer = null; } }
document.getElementById('autorefresh').addEventListener('change', e => { e.target.checked ? startTimer() : stopTimer(); });
tick(); startTimer();
</script>
</body>
</html>
"""


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
                return self._html(INDEX_HTML)
            if path == "/api/projects":
                projects = [project_summary(p) for p in list_projects()]
                projects.sort(key=lambda x: x.get("last_activity_ts") or 0, reverse=True)
                return self._json({"projects": projects, "now": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            if path.startswith("/raw/"):
                rest = path[len("/raw/"):]
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
                rest = path[len("/api/project/"):]
                parts = rest.split("/", 2)
                pid = parts[0]
                if pid not in list_projects():
                    return self._json({"error": "not_found", "id": pid}, code=404)
                if len(parts) == 1:
                    qs = parse_qs(url.query)
                    log_n = int(qs.get("log_lines", ["400"])[0])
                    return self._json(project_detail(pid, log_lines=log_n))
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
