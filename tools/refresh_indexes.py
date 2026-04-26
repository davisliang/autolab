#!/usr/bin/env python3
"""Regenerate index files.

  thread  -> projects/<id>/thread/INDEX.md
  papers  -> projects/<id>/papers/INDEX.md
  global  -> projects/INDEX.md  (one row per project, no AUTOLAB_PROJECT needed)

Usage:
    tools/refresh_indexes.py             # all three (uses AUTOLAB_PROJECT for thread/papers)
    tools/refresh_indexes.py --thread
    tools/refresh_indexes.py --papers
    tools/refresh_indexes.py --projects
"""
from __future__ import annotations

import argparse
import json
import os

from _paths import (
    PROJECTS,
    list_projects,
    papers_dir,
    papers_index,
    project_dir,
    thread_index,
    thread_log,
)


def refresh_thread():
    log = thread_log()
    idx = thread_index()
    idx.parent.mkdir(parents=True, exist_ok=True)
    if not log.exists():
        idx.write_text("# thread/log.jsonl is empty\n")
        return
    by_type: dict[str, list[dict]] = {}
    with log.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            by_type.setdefault(row["type"], []).append(row)

    out = ["# Thread index", ""]
    out.append(f"_{sum(len(v) for v in by_type.values())} artifacts_  ")
    out.append("")
    order = [
        "Idea",
        "Hypothesis",
        "LitFinding",
        "Citation",
        "Critique",
        "ExperimentPlan",
        "ExperimentResult",
        "DraftSection",
    ]
    for t in order:
        rows = by_type.get(t, [])
        if not rows:
            continue
        out.append(f"## {t} ({len(rows)})")
        out.append("")
        out.append("| id | author | summary |")
        out.append("|----|--------|---------|")
        for r in rows:
            sm = r.get("summary", "").replace("|", "\\|")
            out.append(f"| `{r['id']}` | {r.get('author','?')} | {sm} |")
        out.append("")
    idx.write_text("\n".join(out))


def refresh_papers():
    pdir = papers_dir()
    pdir.mkdir(parents=True, exist_ok=True)
    metas = sorted(pdir.glob("*.meta.json"))
    out = ["# Paper cache", ""]
    if not metas:
        out.append("_(empty)_")
        papers_index().write_text("\n".join(out) + "\n")
        return
    out.append("| arxiv_id | title | authors | year |")
    out.append("|----------|-------|---------|------|")
    for m in metas:
        try:
            meta = json.loads(m.read_text())
        except json.JSONDecodeError:
            continue
        aid = m.stem.replace(".meta", "")
        title = (meta.get("title") or "").replace("|", "\\|")
        authors = ", ".join(
            a.get("name", "") for a in meta.get("authors", [])[:3]
        )
        if len(meta.get("authors", [])) > 3:
            authors += ", et al."
        year = (meta.get("publishedAt") or "")[:4]
        out.append(f"| `{aid}` | {title} | {authors} | {year} |")
    papers_index().write_text("\n".join(out) + "\n")


def refresh_projects():
    """Build projects/INDEX.md without needing AUTOLAB_PROJECT."""
    PROJECTS.mkdir(parents=True, exist_ok=True)
    idx = PROJECTS / "INDEX.md"
    rows = []
    for pid in list_projects():
        log = project_dir(pid) / "thread" / "log.jsonl"
        ckpt_dir = project_dir(pid) / "thread" / "checkpoints"
        seed = ""
        latest_phase = "(none)"
        n_artifacts = 0
        if log.exists():
            with log.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    n_artifacts += 1
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if row.get("type") == "Idea" and not seed:
                        seed = row.get("summary", "")
        if ckpt_dir.exists():
            ckpts = sorted(ckpt_dir.glob("*.json"))
            if ckpts:
                latest_phase = ckpts[-1].stem
        rows.append((pid, seed, latest_phase, n_artifacts))

    out = ["# Projects", ""]
    if not rows:
        out.append("_(none yet — use `./start --idea \"...\"`)_")
        idx.write_text("\n".join(out) + "\n")
        return
    out.append("| project | seed idea | latest phase | artifacts |")
    out.append("|---------|-----------|--------------|-----------|")
    for pid, seed, phase, n in rows:
        s = (seed or "").replace("|", "\\|")
        out.append(f"| `{pid}` | {s} | {phase} | {n} |")
    idx.write_text("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thread", action="store_true")
    ap.add_argument("--papers", action="store_true")
    ap.add_argument("--projects", action="store_true")
    args = ap.parse_args()
    if not (args.thread or args.papers or args.projects):
        args.thread = args.papers = args.projects = True
    if args.thread and os.environ.get("AUTOLAB_PROJECT"):
        refresh_thread()
    if args.papers and os.environ.get("AUTOLAB_PROJECT"):
        refresh_papers()
    if args.projects:
        refresh_projects()


if __name__ == "__main__":
    main()
