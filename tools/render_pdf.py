#!/usr/bin/env python3
"""Render a project's paper-vFINAL.md to PDF via pandoc.

Standalone utility — invoke after `./start` finishes (or any time after the
`final` phase) to (re)generate the PDF without re-running the orchestrator.

Usage:
    AUTOLAB_PROJECT=<id> uv run python tools/render_pdf.py
    uv run python tools/render_pdf.py --project <id>
    uv run python tools/render_pdf.py --project <id> --in custom.md --out custom.pdf
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import drafts_dir, project_dir
from run_orchestrator import render_pdf


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", help="project id (defaults to $AUTOLAB_PROJECT)")
    ap.add_argument("--in", dest="in_md", help="markdown input path (default: drafts/paper-vFINAL.md)")
    ap.add_argument("--out", dest="out_pdf", help="pdf output path (default: drafts/paper-vFINAL.pdf)")
    ap.add_argument("--bib", help="bibtex path (default: drafts/citations.bib)")
    args = ap.parse_args()

    pid = args.project or os.environ.get("AUTOLAB_PROJECT", "").strip()
    if not pid:
        ap.error("--project required (or set AUTOLAB_PROJECT)")
    os.environ["AUTOLAB_PROJECT"] = pid

    if not project_dir(pid).exists():
        sys.exit(f"project not found: {pid}")

    drafts = drafts_dir(pid)
    md = Path(args.in_md) if args.in_md else drafts / "paper-vFINAL.md"
    pdf = Path(args.out_pdf) if args.out_pdf else drafts / "paper-vFINAL.pdf"
    bib = Path(args.bib) if args.bib else drafts / "citations.bib"

    if not md.exists():
        sys.exit(f"markdown not found: {md} — has phase_final run yet?")

    print(f"rendering {md} → {pdf}")
    err = render_pdf(md, bib, pdf)
    if err:
        sys.exit(f"PDF render failed: {err}")
    print(f"wrote {pdf} ({pdf.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
