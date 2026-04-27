#!/usr/bin/env python3
"""Reproduce a single `claude -p` call with the orchestrator's exact flags
and show full stdout/stderr/exit code. Use this to diagnose why a phase fails.

Usage:
    AUTOLAB_PROJECT=<id> tools/debug_claude.py
    AUTOLAB_PROJECT=<id> tools/debug_claude.py --model sonnet --prompt "Hello, are you alive?"

Prints the system prompt size, the command line, and the raw subprocess output.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from _paths import PROGRAM, REPO, get_project_id


def project_paths_block() -> str:
    pid = get_project_id()
    base = f"projects/{pid}"
    return (
        f"\n## Active project\nProject id: `{pid}`\nProject root: `{base}/`\n"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="sonnet")
    ap.add_argument(
        "--prompt",
        default="Reply with the single word OK and nothing else.",
        help="User prompt for the test call (kept short to minimize spend)",
    )
    ap.add_argument(
        "--no-system-prompt",
        action="store_true",
        help="Skip --append-system-prompt to test if program.md is the issue",
    )
    args = ap.parse_args()

    pid = get_project_id()
    sys_prompt = "" if args.no_system_prompt else PROGRAM.read_text() + "\n" + project_paths_block()

    cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "--model",
        args.model,
        "--output-format",
        "json",
    ]
    if sys_prompt:
        cmd += ["--append-system-prompt", sys_prompt]
    cmd += ["-p", args.prompt]

    print(f"AUTOLAB_PROJECT = {pid}")
    print(f"system_prompt size: {len(sys_prompt)} chars")
    print(f"user_prompt size: {len(args.prompt)} chars")
    print(f"command (system_prompt elided):")
    safe_cmd = [
        "<<system_prompt>>" if (i > 0 and cmd[i - 1] == "--append-system-prompt") else x
        for i, x in enumerate(cmd)
    ]
    print(f"  {' '.join(repr(x) for x in safe_cmd)}")
    print()

    env = os.environ.copy()
    env["AUTOLAB_PROJECT"] = pid

    r = subprocess.run(
        cmd,
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"exit code: {r.returncode}")
    print()
    print("=== stdout ===")
    print(r.stdout if r.stdout else "(empty)")
    print()
    print("=== stderr ===")
    print(r.stderr if r.stderr else "(empty)")


if __name__ == "__main__":
    main()
