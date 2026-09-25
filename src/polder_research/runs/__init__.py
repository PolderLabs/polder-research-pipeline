"""Runs — bounded research sessions against a brief."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..atomic import write_atomic
from ..paths import RESEARCH_RUNS_DIR, Workspace, active_workspace, resolve_workspace


def _runs_dir(workspace: Workspace | Path | str | None = None) -> Path:
    selected = workspace if workspace is not None else active_workspace()
    return (
        RESEARCH_RUNS_DIR if selected is None else resolve_workspace(selected).research_path("runs")
    )


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
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Create a new run record."""
    runs_dir = _runs_dir(workspace)
    runs_dir.mkdir(parents=True, exist_ok=True)
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
    write_atomic(runs_dir.joinpath(f"{rid}.json"), record, schema_name="run")
    return rid


def update_run_status(
    run_id: str,
    run_status: str,
    *,
    workspace: Workspace | Path | str | None = None,
) -> None:
    """Update a run's status; records started_at or finished_at."""
    if not isinstance(run_id, str) or not re.fullmatch(
        r"run_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", run_id
    ):
        raise ValueError(f"invalid run record id: {run_id!r}")
    p = _runs_dir(workspace) / f"{run_id}.json"
    rec = json.loads(p.read_text(encoding="utf-8"))
    if rec.get("id") != run_id:
        raise ValueError(f"run identity mismatch: {run_id!r}")
    if rec.get("research_method") == "systematic_evidence_review" and run_status in {
        "active",
        "completed",
    }:
        from ..research_methods import verify_run_protocol

        verify_run_protocol(run_id, workspace=workspace)
        if run_status == "completed":
            from ..research_methods import validate_run_for_completion

            issues = validate_run_for_completion(run_id, workspace=workspace)
            if issues:
                raise ValueError("systematic review is not ready to complete: " + "; ".join(issues))
    rec["run_status"] = run_status
    if run_status == "active" and "started_at" not in rec:
        rec["started_at"] = _now()
    if run_status in ("completed", "aborted", "failed"):
        rec["finished_at"] = _now()
    write_atomic(p, rec, schema_name="run")
