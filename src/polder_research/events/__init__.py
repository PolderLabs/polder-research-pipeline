"""Events — append-only workflow event log."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..agents import get_code_revision, get_instruction_version
from ..atomic import write_atomic
from ..paths import REPO_ROOT, RESEARCH_EVENTS_DIR, Workspace, active_workspace, resolve_workspace


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def _config_version(workspace: Workspace | Path | str | None) -> str:
    root = resolve_workspace(workspace).root if workspace is not None else REPO_ROOT
    config = root / "knowledge-base" / "research.config.yaml"
    try:
        digest = hashlib.sha256(config.read_bytes()).hexdigest()
    except OSError:
        return "unavailable"
    return f"sha256:{digest}"


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
    metadata: dict[str, Any] | None = None,
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Append a typed event to the .research/events/ log."""
    selected = workspace if workspace is not None else active_workspace()
    events_dir = (
        RESEARCH_EVENTS_DIR
        if selected is None
        else resolve_workspace(selected).research_path("events")
    )
    events_dir.mkdir(parents=True, exist_ok=True)
    eid = _uuid7("evt")
    record: dict[str, Any] = {
        "id": eid,
        "event_type": event_type,
        "actor": actor,
        "timestamp": _now(),
        "instruction_version": get_instruction_version(role) if role else "unassigned",
        "config_version": _config_version(selected),
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
    if metadata:
        record["metadata"] = metadata
    write_atomic(events_dir.joinpath(f"{eid}.json"), record, schema_name="event")
    return eid
