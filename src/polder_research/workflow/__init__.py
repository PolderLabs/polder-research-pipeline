"""Workflow state builder — derives state snapshot from control-plane records."""

from __future__ import annotations

import json
from pathlib import Path

from ..paths import (
    RESEARCH_DIR,
    RESEARCH_STATE,
    RESEARCH_EVENTS_DIR,
    RESEARCH_TASKS_DIR,
    RESEARCH_RUNS_DIR,
    RESEARCH_HANDOFFS_DIR,
)


def build_state() -> dict:
    """Build a derived state snapshot from .research/ control-plane records."""
    events = list(RESEARCH_EVENTS_DIR.glob("*.json"))
    tasks = list(RESEARCH_TASKS_DIR.glob("*.json"))
    runs = list(RESEARCH_RUNS_DIR.glob("*.json"))
    handoffs = list(RESEARCH_HANDOFFS_DIR.glob("*.json"))

    run_by_status: dict[str, int] = {}
    for p in runs:
        rec = json.loads(p.read_text())
        s = rec.get("run_status", "unknown")
        run_by_status[s] = run_by_status.get(s, 0) + 1

    task_by_status: dict[str, int] = {}
    for p in tasks:
        rec = json.loads(p.read_text())
        s = rec.get("status", "unknown")
        task_by_status[s] = task_by_status.get(s, 0) + 1

    handoff_by_status: dict[str, int] = {}
    for p in handoffs:
        rec = json.loads(p.read_text())
        s = rec.get("status", "unknown")
        handoff_by_status[s] = handoff_by_status.get(s, 0) + 1

    return {
        "schema_version": 1,
        "runs": {"total": len(runs), "by_status": run_by_status},
        "tasks": {"total": len(tasks), "by_status": task_by_status},
        "handoffs": {"total": len(handoffs), "by_status": handoff_by_status},
        "events": {"total": len(events)},
    }


def save_state() -> None:
    """Write the current state snapshot to .research/state.json."""
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    RESEARCH_STATE.write_text(json.dumps(build_state(), indent=2))
