"""Health check builder — derives health snapshot from control-plane records."""

from __future__ import annotations

import json
from pathlib import Path

from ..paths import (
    RESEARCH_DIR,
    RESEARCH_HEALTH,
    RESEARCH_TASKS_DIR,
    RESEARCH_RUNS_DIR,
)


def build_health() -> dict:
    """Build a health snapshot. Returns degraded if any tasks/runs are failed."""
    tasks = list(RESEARCH_TASKS_DIR.glob("*.json"))
    runs = list(RESEARCH_RUNS_DIR.glob("*.json"))

    failed_tasks = sum(
        1 for p in tasks
        if json.loads(p.read_text()).get("status") == "failed"
    )
    failed_runs = sum(
        1 for p in runs
        if json.loads(p.read_text()).get("run_status") == "failed"
    )

    issues: list[str] = []
    if failed_tasks:
        issues.append(f"{failed_tasks} failed task(s)")
    if failed_runs:
        issues.append(f"{failed_runs} failed run(s)")

    return {
        "schema_version": 1,
        "overall": "degraded" if issues else "ok",
        "issues": issues,
    }


def save_health() -> None:
    """Write the current health snapshot to .research/health.json."""
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    RESEARCH_HEALTH.write_text(json.dumps(build_health(), indent=2))
