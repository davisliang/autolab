"""autolab — autonomous research loop driven by Claude subagents.

The orchestrator (`autolab.orchestrator`) drives a fixed phase pipeline
(seed → expand → survey → screen → design → run → critique → write → final)
backed by a typed-artifact thread on disk under `projects/<id>/`.

Public CLI entry points (invoked from `scripts/start` and `scripts/resume`):
    python -m autolab.orchestrator
    python -m autolab.refresh_indexes
    python -m autolab.finalize
    python -m autolab.idle_continue
    python -m autolab.dashboard.server
"""

__version__ = "0.1.0"
