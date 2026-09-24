"""Handoffs — typed transfers of work between roles."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from ..atomic import write_atomic
from ..paths import RESEARCH_HANDOFFS_DIR


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def write_handoff(
    from_role: str,
    to_role: str,
    summary: str,
    *,
    context: dict[str, Any] | None = None,
    artifacts: list[str] | None = None,
) -> str:
    """Create a new handoff record."""
    RESEARCH_HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)
    hid = _uuid7("hnd")
    record: dict[str, Any] = {
        "id": hid,
        "schema_version": 1,
        "from_role": from_role,
        "to_role": to_role,
        "status": "open",
        "summary": summary,
        "created_at": _now(),
    }
    if context:
        record["context"] = context
    if artifacts:
        record["artifacts"] = artifacts
    write_atomic(RESEARCH_HANDOFFS_DIR.joinpath(f"{hid}.json"), record, schema_name="handoff")
    return hid


def accept_handoff(handoff_id: str) -> None:
    _validate_handoff_id(handoff_id)
    p = RESEARCH_HANDOFFS_DIR / f"{handoff_id}.json"
    rec = json.loads(p.read_text())
    if rec.get("id") != handoff_id:
        raise ValueError(f"handoff identity mismatch: {handoff_id!r}")
    rec["status"] = "accepted"
    rec["accepted_at"] = _now()
    write_atomic(p, rec, schema_name="handoff")


def reject_handoff(handoff_id: str, reason: str) -> None:
    _validate_handoff_id(handoff_id)
    p = RESEARCH_HANDOFFS_DIR / f"{handoff_id}.json"
    rec = json.loads(p.read_text())
    if rec.get("id") != handoff_id:
        raise ValueError(f"handoff identity mismatch: {handoff_id!r}")
    rec["status"] = "rejected"
    rec["rejection_reason"] = reason
    write_atomic(p, rec, schema_name="handoff")


def _validate_handoff_id(handoff_id: str) -> None:
    if not isinstance(handoff_id, str) or not re.fullmatch(
        r"hnd_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        handoff_id,
    ):
        raise ValueError(f"invalid handoff record id: {handoff_id!r}")
