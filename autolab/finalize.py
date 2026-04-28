#!/usr/bin/env python3
"""Regenerate `drafts/paper-vFINAL.md` for an existing project.

Re-runs `phase_final()` against the current thread state. Useful when you
have edited DraftSection bodies and want to re-assemble the markdown without
re-running earlier phases.

Usage:
    uv run python -m autolab.finalize --project <id>
    AUTOLAB_PROJECT=<id> uv run python -m autolab.finalize
"""

from __future__ import annotations

import argparse
import os
import sys

from autolab.orchestrator import phase_final
from autolab.paths import project_dir


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
    for p in phase_final():
        print(f"  wrote {p}")


if __name__ == "__main__":
    main()
