"""Tasks — work units within a run, with optional lease."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from ..atomic import write_atomic
from ..locking import LockBusyError, acquire_file_lock, release_file_lock
from ..paths import RESEARCH_LOCKS_DIR, RESEARCH_TASKS_DIR


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def _validate_task_id(task_id: str) -> None:
    if not isinstance(task_id, str) or not re.fullmatch(
        r"tsk_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        task_id,
    ):
        raise ValueError(f"invalid task record id: {task_id!r}")


def _require_task(task_id: str) -> dict[str, Any]:
    """Verify that a task record exists on disk and matches its id.

    Per AUDIT.md §16: foreign-key references must resolve before a child
    operation (acquire_lease, update_task_status) proceeds. Returns the
    parsed record.
    """
    _validate_task_id(task_id)
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

    guard = acquire_file_lock(RESEARCH_LOCKS_DIR / "task-create.lock", wait=True)
    try:
        wanted = _sig(task_kind, role, summary)
        for existing in RESEARCH_TASKS_DIR.glob("tsk_*.json"):
            try:
                rec = json.loads(existing.read_text(encoding="utf-8"))
            except OSError, json.JSONDecodeError:
                continue
            if rec.get("status") in ("completed", "failed", "abandoned"):
                continue
            if (
                _sig(rec.get("task_kind", ""), rec.get("role", ""), rec.get("summary", ""))
                == wanted
            ):
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
    finally:
        release_file_lock(guard)


def update_task_status(task_id: str, status: str) -> None:
    """Update a task's status field."""
    _validate_task_id(task_id)
    guard = acquire_file_lock(RESEARCH_LOCKS_DIR / f"task-{task_id}.lock", wait=True)
    try:
        rec = _require_task(task_id)
        rec["status"] = status
        rec["updated_at"] = _now()
        _write(task_id, rec)
    finally:
        release_file_lock(guard)


def acquire_lease(task_id: str, leaser: str, ttl_seconds: int) -> str:
    """Acquire an exclusive lease on a task. Returns lease token.

    Enforces the canonical ``task.lease`` schema (AUDIT.md §7, §20): only
    ``leaser``, ``leased_at``, ``expires_at``, ``lease_token`` are written;
    mutual exclusion is real (rejects if a non-expired lease is already held).
    """
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds < 1:
        raise ValueError("ttl_seconds must be a positive integer")
    if not isinstance(leaser, str) or not leaser.strip():
        raise ValueError("leaser must be a non-empty identity")
    _validate_task_id(task_id)
    try:
        guard = acquire_file_lock(RESEARCH_LOCKS_DIR / f"task-{task_id}.lock", wait=True)
    except LockBusyError as exc:
        raise PermissionError(f"task {task_id} lease is being updated by another process") from exc
    try:
        rec = _require_task(task_id)
        existing = rec.get("lease") or {}
        if existing.get("expires_at"):
            if datetime.fromisoformat(existing["expires_at"]) > datetime.now(UTC):
                raise PermissionError(
                    f"task {task_id} already leased by {existing.get('leaser')!r}"
                )
        token = _uuid7("lse")
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=ttl_seconds)
        rec["status"] = "leased"
        rec["lease"] = {
            "leaser": leaser.strip(),
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
                "leaser": leaser.strip(),
                "leased_at": _now(),
                "expires_at": expires.isoformat(),
            },
        )
        return token
    finally:
        release_file_lock(guard)


def release_lease(task_id: str, lease_token: str | None = None) -> None:
    """Release a task lease; supplying its token prevents stale-owner release.

    Omitting the token is retained for administrative recovery compatibility.
    Agent workers should always pass the token returned by ``acquire_lease``.
    """
    _validate_task_id(task_id)
    try:
        guard = acquire_file_lock(RESEARCH_LOCKS_DIR / f"task-{task_id}.lock", wait=True)
    except LockBusyError as exc:
        raise PermissionError(f"task {task_id} lease is being updated by another process") from exc
    try:
        rec = _require_task(task_id)
        lease = rec.get("lease") or {}
        if not lease:
            raise ValueError(f"task {task_id} has no active lease")
        if lease_token is not None and lease.get("lease_token") != lease_token:
            raise PermissionError("lease token does not match the current task owner")
        rec["status"] = "pending"
        rec["updated_at"] = _now()
        rec.pop("lease", None)
        _write(task_id, rec)
    finally:
        release_file_lock(guard)
