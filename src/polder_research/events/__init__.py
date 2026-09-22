"""Events — append-only workflow event log."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from ..agents import get_code_revision, get_instruction_version
from ..atomic import write_atomic
from ..paths import RESEARCH_EVENTS_DIR


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def write_event(
    event_type: str,
    actor: str,
    *,
    role: str | None = None,
    run_id: str | None = None,
    task_id: str | None = None,
    action: str | None = None,
    summary: str | None = None,
    result: str = "ok",
    targets: list[str] | None = None,
    error_category: str | None = None,
    error_message: str | None = None,
) -> str:
    """Append a typed event to the .research/events/ log."""
    RESEARCH_EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    eid = _uuid7("evt")
    record: dict[str, Any] = {
        "id": eid,
        "event_type": event_type,
        "actor": actor,
        "timestamp": _now(),
        "instruction_version": get_instruction_version(role) if role else "0.1.0",
        "code_revision": get_code_revision(),
    }
    if role:
        record["role"] = role
    if run_id:
        record["run_id"] = run_id
    if task_id:
        record["task_id"] = task_id
    if action:
        record["action"] = action
    if summary:
        record["summary"] = summary
    record["result"] = result
    if targets:
        record["targets"] = targets
    if error_message:
        record["error"] = {
            "sanitized_message": error_message,
            "category": error_category or "internal",
        }
    write_atomic(RESEARCH_EVENTS_DIR.joinpath(f"{eid}.json"), record, schema_name="event")
    return eid
