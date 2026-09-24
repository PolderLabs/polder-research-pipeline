"""Runs — bounded research sessions against a brief."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from ..atomic import write_atomic
from ..paths import RESEARCH_RUNS_DIR


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def write_run(
    brief: dict[str, Any],
    run_status: str = "draft",
    *,
    research_method: str = "continuous_intelligence",
    outputs: list[str] | None = None,
) -> str:
    """Create a new run record."""
    RESEARCH_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    rid = _uuid7("run")
    if research_method == "systematic_evidence_review" and run_status != "draft":
        raise ValueError(
            "systematic evidence review runs must be created as draft, then protocol-frozen"
        )
    record: dict[str, Any] = {
        "id": rid,
        "schema_version": 1,
        "run_status": run_status,
        "research_method": research_method,
        "brief": brief,
        "created_at": _now(),
    }
    if outputs:
        record["outputs"] = list(outputs)
    write_atomic(RESEARCH_RUNS_DIR.joinpath(f"{rid}.json"), record, schema_name="run")
    return rid


def update_run_status(run_id: str, run_status: str) -> None:
    """Update a run's status; records started_at or finished_at."""
    p = RESEARCH_RUNS_DIR / f"{run_id}.json"
    rec = json.loads(p.read_text(encoding="utf-8"))
    if rec.get("id") != run_id:
        raise ValueError(f"run identity mismatch: {run_id!r}")
    if rec.get("research_method") == "systematic_evidence_review" and run_status in {
        "active",
        "completed",
    }:
        from ..research_methods import verify_run_protocol

        verify_run_protocol(run_id)
        if run_status == "completed":
            from ..research_methods import validate_run_for_completion

            issues = validate_run_for_completion(run_id)
            if issues:
                raise ValueError("systematic review is not ready to complete: " + "; ".join(issues))
    rec["run_status"] = run_status
    if run_status == "active" and "started_at" not in rec:
        rec["started_at"] = _now()
    if run_status in ("completed", "aborted", "failed"):
        rec["finished_at"] = _now()
    write_atomic(p, rec, schema_name="run")
