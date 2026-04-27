#!/usr/bin/env python3
"""Regenerate paper-vFINAL.md (and PDF if pandoc is available) for an existing
project, without re-running the orchestrator. Useful when you've updated the
table generator or section assembly logic and want to refresh the output of
`phase_final` for a project that already finished.

Usage:
    uv run python tools/regenerate_final.py --project <id>
    AUTOLAB_PROJECT=<id> uv run python tools/regenerate_final.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import drafts_dir, project_dir
from run_orchestrator import phase_final


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", help="project id (defaults to $AUTOLAB_PROJECT)")
    args = ap.parse_args()
    pid = args.project or os.environ.get("AUTOLAB_PROJECT", "").strip()
    if not pid:
        ap.error("--project required (or set AUTOLAB_PROJECT)")
    os.environ["AUTOLAB_PROJECT"] = pid
    if not project_dir(pid).exists():
        sys.exit(f"project not found: {pid}")
    print(f"regenerating phase_final for {pid}…")
    out_paths = phase_final()
    for p in out_paths:
        print(f"  wrote {p}")


if __name__ == "__main__":
    main()
