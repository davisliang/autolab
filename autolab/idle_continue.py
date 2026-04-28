#!/usr/bin/env python3
"""CPU-idle watchdog: re-invoke continue_loop.sh after N seconds of low CPU.

Project-scoped: requires AUTOLAB_PROJECT env var (set by ./resume --watchdog).
Stops on the active project's final.json, on STOP file, or on max-respawns.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import UTC, datetime

import psutil

from autolab.paths import (
    REPO,
    STOP_FILE,
    checkpoints_dir,
    get_project_id,
    watchdog_log,
)

LOOP = REPO / "scripts" / "continue_loop.sh"


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def log(msg: str):
    p = watchdog_log()
    p.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{now_iso()}] {msg}\n"
    with p.open("a") as f:
        f.write(line)
    sys.stdout.write(line)
    sys.stdout.flush()


def is_done() -> str | None:
    if (checkpoints_dir() / "final.json").exists():
        return "final.json present"
    if STOP_FILE.exists():
        return "STOP file present"
    return None


def spawn_loop() -> int:
    log("spawning continue_loop.sh")
    r = subprocess.run(["bash", str(LOOP)], cwd=REPO)
    log(f"continue_loop.sh exited rc={r.returncode}")
    return r.returncode


def cpu_idle_pct(window_s: float = 1.0) -> float:
    return 100.0 - psutil.cpu_percent(interval=window_s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idle-seconds", type=int, default=300)
    ap.add_argument(
        "--idle-pct",
        type=float,
        default=95.0,
        help="CPU must be at least this %% idle for idle-seconds before respawn",
    )
    ap.add_argument("--max-respawns", type=int, default=20)
    args = ap.parse_args()

    # validate AUTOLAB_PROJECT now so failures show early
    pid = get_project_id()
    log(f"watchdog start: project={pid}")

    runs = 0
    while True:
        reason = is_done()
        if reason:
            log(f"done: {reason}")
            return
        if runs >= args.max_respawns:
            log(f"max-respawns reached ({args.max_respawns})")
            return
        spawn_loop()
        runs += 1

        reason = is_done()
        if reason:
            log(f"done after run: {reason}")
            return

        log(f"waiting for {args.idle_seconds}s of >{args.idle_pct:.0f}% idle CPU")
        idle_streak = 0.0
        while idle_streak < args.idle_seconds:
            idle = cpu_idle_pct(window_s=1.0)
            if idle >= args.idle_pct:
                idle_streak += 1.0
            else:
                idle_streak = 0.0
            if STOP_FILE.exists():
                log("STOP file appeared during idle wait; exiting")
                return
            time.sleep(1.0)
        log("idle threshold met; respawning")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("interrupted")
        sys.exit(130)
