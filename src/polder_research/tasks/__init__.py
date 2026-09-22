"""Tasks — work units within a run, with optional lease."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from ..atomic import write_atomic
from ..paths import RESEARCH_LOCKS_DIR, RESEARCH_TASKS_DIR


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def _require_task(task_id: str) -> dict[str, Any]:
    """Verify that a task record exists on disk and matches its id.

    Per AUDIT.md §16: foreign-key references must resolve before a child
    operation (acquire_lease, update_task_status) proceeds. Returns the
    parsed record.
    """
    if not task_id or not isinstance(task_id, str):
        raise ValueError(f"task id must be a non-empty string, got {task_id!r}")
    if not task_id.startswith("tsk_"):
        raise ValueError(f"expected tsk_ record id, got {task_id!r}")
    p = RESEARCH_TASKS_DIR / f"{task_id}.json"
    if not p.is_file():
        raise ValueError(f"task record does not exist: {task_id!r}")
    rec = json.loads(p.read_text())
    if rec.get("id") != task_id:
        raise ValueError(f"task identity mismatch: {task_id!r} (file contains {rec.get('id')!r})")
    return rec


def _write(task_id: str, rec: dict[str, Any]) -> None:
    target = RESEARCH_TASKS_DIR / f"{task_id}.json"
    write_atomic(target, rec, schema_name="task")


def write_task(
    task_kind: str,
    status: str,
    role: str,
    summary: str,
    *,
    run_id: str | None = None,
) -> str:
    """Create a new task record. If a task with the same (task_kind, role,
    summary) signature already exists in an open state, return its id instead
    of creating a duplicate (idempotency; AUDIT.md §15). The signature is
    recomputed from each record's own fields — no extra property is stored,
    keeping records schema-clean.
    """
    RESEARCH_TASKS_DIR.mkdir(parents=True, exist_ok=True)

    def _sig(kind: str, r: str, s: str) -> str:
        return hashlib.sha256(f"{kind}|{r}|{s}".encode()).hexdigest()[:16]

    wanted = _sig(task_kind, role, summary)
    for existing in RESEARCH_TASKS_DIR.glob("tsk_*.json"):
        try:
            rec = json.loads(existing.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if rec.get("status") in ("completed", "failed", "abandoned"):
            continue
        if _sig(rec.get("task_kind", ""), rec.get("role", ""), rec.get("summary", "")) == wanted:
            return rec["id"]
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
    rec = _require_task(task_id)
    rec["status"] = status
    rec["updated_at"] = _now()
    _write(task_id, rec)


def acquire_lease(task_id: str, leaser: str, ttl_seconds: int) -> str:
    """Acquire an exclusive lease on a task. Returns lease token.

    Enforces the canonical ``task.lease`` schema (AUDIT.md §7, §20): only
    ``leaser``, ``leased_at``, ``expires_at``, ``lease_token`` are written;
    mutual exclusion is real (rejects if a non-expired lease is already held).
    """
    RESEARCH_LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    rec = _require_task(task_id)
    existing = rec.get("lease") or {}
    if existing.get("expires_at"):
        if datetime.fromisoformat(existing["expires_at"]) > datetime.now(UTC):
            raise PermissionError(f"task {task_id} already leased by {existing.get('leaser')!r}")
    token = _uuid7("lse")
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=ttl_seconds)
    rec["status"] = "leased"
    rec["lease"] = {
        "leaser": leaser,
        "leased_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expires_at": expires.isoformat(),
        "lease_token": token,
    }
    rec["updated_at"] = _now()
    _write(task_id, rec)
    write_atomic(
        RESEARCH_LOCKS_DIR.joinpath(f"{token}.json"),
        {
            "id": token,
            "task_id": task_id,
            "leaser": leaser,
            "leased_at": _now(),
            "expires_at": expires.isoformat(),
        },
    )
    return token


def release_lease(task_id: str) -> None:
    """Release a task's lease, returning it to pending."""
    rec = _require_task(task_id)
    rec["status"] = "pending"
    rec["updated_at"] = _now()
    rec.pop("lease", None)
    _write(task_id, rec)
