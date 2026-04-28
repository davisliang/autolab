#!/usr/bin/env python3
"""Append a typed artifact to the active project's thread/log.jsonl and
write the companion thoughts/<id>.md.

The active project is selected via the AUTOLAB_PROJECT env var (set by the
start/resume scripts). All paths resolve under projects/<id>/.

Usage:
    python -m autolab.append_artifact \
        --type Hypothesis \
        --parent IDEA-001,LIT-014 \
        --author idea-expander \
        --summary "Per-layer LR scaling beats uniform LR on MLP MNIST" \
        --field prediction_metric=val_accuracy \
        --field prediction_threshold=0.3 \
        --field prediction_direction=greater \
        [--body-from-stdin]

Prints the new artifact id (e.g. HYP-003) to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime

from autolab.paths import thoughts_dir, thread_log

TYPE_PREFIX = {
    "Idea": "IDEA",
    "Hypothesis": "HYP",
    "LitFinding": "LIT",
    "Citation": "CITE",
    "ExperimentPlan": "EXP",
    "ExperimentResult": "RES",
    "Critique": "CRIT",
    "DraftSection": "DRAFT",
}


def next_id(artifact_type: str) -> str:
    prefix = TYPE_PREFIX[artifact_type]
    log = thread_log()
    log.parent.mkdir(parents=True, exist_ok=True)
    if not log.exists():
        return f"{prefix}-001"
    max_n = 0
    with log.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = row.get("id", "")
            if rid.startswith(prefix + "-"):
                try:
                    max_n = max(max_n, int(rid.split("-", 1)[1]))
                except ValueError:
                    pass
    return f"{prefix}-{max_n + 1:03d}"


def coerce_value(raw: str):
    """Coerce a CLI --field value to JSON when possible, else string."""
    raw = raw.strip()
    if not raw:
        return ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def parse_fields(field_args: list[str]) -> dict:
    out = {}
    for f in field_args or []:
        if "=" not in f:
            raise SystemExit(f"--field must be key=value, got: {f}")
        k, v = f.split("=", 1)
        out[k.strip()] = coerce_value(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True, choices=list(TYPE_PREFIX.keys()))
    ap.add_argument("--parent", default="", help="Comma-separated parent ids")
    ap.add_argument("--author", required=True, help="Skill or tool that authored this")
    ap.add_argument("--summary", required=True, help="One-line summary")
    ap.add_argument(
        "--field",
        action="append",
        default=[],
        help="Type-specific field as key=value. JSON values supported.",
    )
    ap.add_argument(
        "--body-from-stdin",
        action="store_true",
        help="Read free-form markdown body from stdin into thoughts/<id>.md",
    )
    args = ap.parse_args()

    parents = [p.strip() for p in args.parent.split(",") if p.strip()]
    fields = parse_fields(args.field)

    aid = next_id(args.type)
    thoughts = thoughts_dir()
    thoughts.mkdir(parents=True, exist_ok=True)
    body_rel = f"thoughts/{aid}.md"

    row = {
        "id": aid,
        "type": args.type,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "parent_ids": parents,
        "author": args.author,
        "summary": args.summary,
        "body_path": body_rel,
        **fields,
    }

    log = thread_log()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    body = sys.stdin.read() if args.body_from_stdin else ""
    fm = "---\n" + json.dumps(row, indent=2, ensure_ascii=False) + "\n---\n\n"
    (thoughts / f"{aid}.md").write_text(fm + body)

    print(aid)


if __name__ == "__main__":
    main()
