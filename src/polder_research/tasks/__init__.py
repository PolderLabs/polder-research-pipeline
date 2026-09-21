"""Tasks — work units within a run, with optional lease."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from ..paths import RESEARCH_TASKS_DIR, RESEARCH_LOCKS_DIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def _read(task_id: str) -> dict[str, Any]:
    p = RESEARCH_TASKS_DIR / f"{task_id}.json"
    return json.loads(p.read_text())


def _write(task_id: str, rec: dict[str, Any]) -> None:
    p = RESEARCH_TASKS_DIR / f"{task_id}.json"
    p.write_text(json.dumps(rec, indent=2))


def write_task(
    task_kind: str,
    status: str,
    role: str,
    summary: str,
    *,
    run_id: str | None = None,
) -> str:
    """Create a new task record."""
    RESEARCH_TASKS_DIR.mkdir(parents=True, exist_ok=True)
    tid = _uuid7("tsk")
    record: dict[str, Any] = {
        "id": tid,
        "schema_version": 1,
        "task_kind": task_kind,
        "status": status,
        "role": role,
        "summary": summary,
        "created_at": _now(),
    }
    if run_id:
        record["run_id"] = run_id
    _write(tid, record)
    return tid


def update_task_status(task_id: str, status: str) -> None:
    """Update a task's status field."""
    rec = _read(task_id)
    rec["status"] = status
    rec["updated_at"] = _now()
    if status in ("completed", "failed", "abandoned"):
        rec["completed_at"] = _now()
    _write(task_id, rec)


def acquire_lease(task_id: str, leaser: str, ttl_seconds: int) -> str:
    """Acquire an exclusive lease on a task. Returns lease token."""
    RESEARCH_LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    rec = _read(task_id)
    lid = _uuid7("lse")
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    rec["status"] = "leased"
    rec["lease"] = {
        "id": lid,
        "leaser": leaser,
        "expires_at": expires.isoformat(),
    }
    rec["updated_at"] = _now()
    _write(task_id, rec)
    RESEARCH_LOCKS_DIR.joinpath(f"{lid}.json").write_text(
        json.dumps(
            {
                "id": lid,
                "task_id": task_id,
                "leaser": leaser,
                "expires_at": expires.isoformat(),
                "acquired_at": _now(),
            },
            indent=2,
        )
    )
    return lid


def release_lease(task_id: str) -> None:
    """Release a task's lease, returning it to pending."""
    rec = _read(task_id)
    rec["status"] = "pending"
    rec["updated_at"] = _now()
    rec.pop("lease", None)
    _write(task_id, rec)
