"""Runs — bounded research sessions against a brief."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from ..paths import RESEARCH_RUNS_DIR


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def write_run(
    brief: dict[str, Any],
    run_status: str = "draft",
) -> str:
    """Create a new run record."""
    RESEARCH_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    rid = _uuid7("run")
    record: dict[str, Any] = {
        "id": rid,
        "schema_version": 1,
        "run_status": run_status,
        "brief": brief,
        "created_at": _now(),
    }
    RESEARCH_RUNS_DIR.joinpath(f"{rid}.json").write_text(json.dumps(record, indent=2))
    return rid


def update_run_status(run_id: str, run_status: str) -> None:
    """Update a run's status; records started_at or finished_at."""
    p = RESEARCH_RUNS_DIR / f"{run_id}.json"
    rec = json.loads(p.read_text())
    rec["run_status"] = run_status
    if run_status == "active" and "started_at" not in rec:
        rec["started_at"] = _now()
    if run_status in ("completed", "aborted", "failed"):
        rec["finished_at"] = _now()
    p.write_text(json.dumps(rec, indent=2))
