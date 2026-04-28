#!/usr/bin/env python3
"""Finalize a project: regenerate paper-vFINAL.md and (if pandoc + a TeX engine
are installed) render it to PDF. Replaces the older split scripts
`regenerate_final.py` and `render_pdf.py`.

Default invocation re-runs `phase_final` (which now also tries to render PDF
internally). Use `--pdf-only` to render an existing markdown without
re-running assembly.

Usage:
    uv run python tools/finalize.py --project <id>            # md + pdf
    uv run python tools/finalize.py --project <id> --pdf-only # pdf only
    AUTOLAB_PROJECT=<id> uv run python tools/finalize.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import drafts_dir, project_dir
from run_orchestrator import phase_final, render_pdf


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", help="project id (defaults to $AUTOLAB_PROJECT)")
    ap.add_argument(
        "--pdf-only",
        action="store_true",
        help="render existing paper-vFINAL.md to PDF only; skip markdown regeneration",
    )
    args = ap.parse_args()

    pid = args.project or os.environ.get("AUTOLAB_PROJECT", "").strip()
    if not pid:
        ap.error("--project required (or set AUTOLAB_PROJECT)")
    os.environ["AUTOLAB_PROJECT"] = pid

    if not project_dir(pid).exists():
        sys.exit(f"project not found: {pid}")

    drafts = drafts_dir(pid)
    md = drafts / "paper-vFINAL.md"
    pdf = drafts / "paper-vFINAL.pdf"
    bib = drafts / "citations.bib"

    if args.pdf_only:
        if not md.exists():
            sys.exit(f"markdown not found: {md} — run without --pdf-only first")
        print(f"rendering {md} → {pdf}")
        err = render_pdf(md, bib, pdf)
        if err:
            sys.exit(f"PDF render failed: {err}")
        print(f"wrote {pdf} ({pdf.stat().st_size:,} bytes)")
        return

    print(f"regenerating phase_final for {pid}…")
    out_paths = phase_final()
    for p in out_paths:
        print(f"  wrote {p}")


if __name__ == "__main__":
    main()
