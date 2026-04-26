"""Project-scoped path helpers.

Each autolab "project" is one full run on one seed idea. Projects live under
`projects/<project-id>/` and contain their own thread/papers/thoughts/etc.

Selection: tools resolve the active project via the `AUTOLAB_PROJECT` env var.
The `start` and `resume` shell scripts set this; `claude -p` subprocesses
spawned by the orchestrator inherit it.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROJECTS = REPO / "projects"
PROGRAM = REPO / "program.md"
TOOLS = REPO / "tools"
SKILLS = REPO / "skills"
STOP_FILE = REPO / "STOP"


def get_project_id() -> str:
    pid = os.environ.get("AUTOLAB_PROJECT", "").strip()
    if not pid:
        raise SystemExit(
            "AUTOLAB_PROJECT env var is required. Use ./start or ./resume scripts."
        )
    return pid


def project_dir(project_id: str | None = None) -> Path:
    p = PROJECTS / (project_id or get_project_id())
    return p


def thread_dir(project_id: str | None = None) -> Path:
    return project_dir(project_id) / "thread"


def thread_log(project_id: str | None = None) -> Path:
    return thread_dir(project_id) / "log.jsonl"


def thread_index(project_id: str | None = None) -> Path:
    return thread_dir(project_id) / "INDEX.md"


def checkpoints_dir(project_id: str | None = None) -> Path:
    return thread_dir(project_id) / "checkpoints"


def thoughts_dir(project_id: str | None = None) -> Path:
    return project_dir(project_id) / "thoughts"


def papers_dir(project_id: str | None = None) -> Path:
    return project_dir(project_id) / "papers"


def papers_index(project_id: str | None = None) -> Path:
    return papers_dir(project_id) / "INDEX.md"


def experiments_dir(project_id: str | None = None) -> Path:
    return project_dir(project_id) / "experiments"


def drafts_dir(project_id: str | None = None) -> Path:
    return project_dir(project_id) / "drafts"


def ideas_dir(project_id: str | None = None) -> Path:
    return project_dir(project_id) / "ideas"


def parking_lot(project_id: str | None = None) -> Path:
    return ideas_dir(project_id) / "parking_lot.md"


def logs_dir(project_id: str | None = None) -> Path:
    return project_dir(project_id) / "logs"


def cost_ledger(project_id: str | None = None) -> Path:
    return logs_dir(project_id) / "cost_ledger.tsv"


def orchestrator_log(project_id: str | None = None) -> Path:
    return logs_dir(project_id) / "orchestrator.log"


def watchdog_log(project_id: str | None = None) -> Path:
    return logs_dir(project_id) / "watchdog.log"


def slugify(text: str, max_words: int = 6) -> str:
    """Make a short filesystem-safe slug from a free-form idea string."""
    text = text.lower().strip()
    words = re.findall(r"[a-z0-9]+", text)
    if not words:
        return "idea"
    return "-".join(words[:max_words])


def make_project_id(seed_idea: str) -> str:
    """Build a unique project id: <slug>-<YYYYMMDD>, suffixed with -2/-3 on collision."""
    slug = slugify(seed_idea)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    base = f"{slug}-{date}"
    PROJECTS.mkdir(parents=True, exist_ok=True)
    candidate = base
    i = 2
    while (PROJECTS / candidate).exists():
        candidate = f"{base}-{i}"
        i += 1
    return candidate


def list_projects() -> list[str]:
    if not PROJECTS.exists():
        return []
    return sorted(p.name for p in PROJECTS.iterdir() if p.is_dir())


def init_project_dir(project_id: str) -> Path:
    """Create a fresh project subtree."""
    pdir = PROJECTS / project_id
    for sub in [
        "thread/checkpoints",
        "papers",
        "thoughts",
        "experiments",
        "drafts",
        "ideas",
        "logs",
    ]:
        (pdir / sub).mkdir(parents=True, exist_ok=True)
    pl = pdir / "ideas" / "parking_lot.md"
    if not pl.exists():
        pl.write_text("")
    return pdir
