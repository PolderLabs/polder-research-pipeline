"""Handoffs — typed transfers of work between roles."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

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
    RESEARCH_HANDOFFS_DIR.joinpath(f"{hid}.json").write_text(json.dumps(record, indent=2))
    return hid


def accept_handoff(handoff_id: str) -> None:
    p = RESEARCH_HANDOFFS_DIR / f"{handoff_id}.json"
    rec = json.loads(p.read_text())
    rec["status"] = "accepted"
    rec["accepted_at"] = _now()
    p.write_text(json.dumps(rec, indent=2))


def reject_handoff(handoff_id: str, reason: str) -> None:
    p = RESEARCH_HANDOFFS_DIR / f"{handoff_id}.json"
    rec = json.loads(p.read_text())
    rec["status"] = "rejected"
    rec["rejection_reason"] = reason
    p.write_text(json.dumps(rec, indent=2))
