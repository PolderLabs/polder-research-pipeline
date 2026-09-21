"""Evidence primitives — source, claim, entity, gap, conflict, segment."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..paths import (
    EVIDENCE_SOURCES_DIR,
    EVIDENCE_CLAIMS_DIR,
    EVIDENCE_ENTITIES_DIR,
    EVIDENCE_SEGMENTS_DIR,
    EVIDENCE_GAPS_DIR,
    EVIDENCE_CONFLICTS_DIR,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def compute_content_hash(content: bytes | Path) -> str:
    """Compute SHA-256 of raw bytes or a file."""
    if isinstance(content, Path):
        content = content.read_bytes()
    return hashlib.sha256(content).hexdigest()


def ensure_evidence_dirs() -> None:
    """Create all evidence subdirectories under .research/."""
    for d in (
        EVIDENCE_SOURCES_DIR,
        EVIDENCE_CLAIMS_DIR,
        EVIDENCE_ENTITIES_DIR,
        EVIDENCE_SEGMENTS_DIR,
        EVIDENCE_GAPS_DIR,
        EVIDENCE_CONFLICTS_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def register_source(
    *,
    title: str,
    source_type: str,
    media_type: str,
    raw_bytes: bytes | None = None,
    doi: str | None = None,
    canonical_url: str | None = None,
    content_sha256: str | None = None,
) -> str:
    """Register a new source record, compute content hash if raw_bytes provided."""
    ensure_evidence_dirs()
    sid = _uuid7("src")
    if raw_bytes is not None:
        content_sha256 = compute_content_hash(raw_bytes)
    record: dict[str, Any] = {
        "id": sid,
        "schema_version": 1,
        "source_status": "current",
        "source_type": source_type,
        "media_type": media_type,
        "title": title,
        "retrieved_at": _now(),
        "content_sha256": content_sha256 or "",
    }
    if doi:
        record["doi"] = doi
    if canonical_url:
        record["canonical_url"] = canonical_url
    EVIDENCE_SOURCES_DIR.joinpath(f"{sid}.json").write_text(
        json.dumps(record, indent=2)
    )
    return sid


def find_duplicate_source(
    *,
    doi: str | None = None,
    canonical_url: str | None = None,
    content_sha256: str | None = None,
) -> str | None:
    """Find an existing source by DOI, URL, or SHA-256. Returns id or None."""
    if doi:
        for p in EVIDENCE_SOURCES_DIR.glob("src_*.json"):
            rec = json.loads(p.read_text())
            if rec.get("doi") == doi:
                return rec["id"]
    if canonical_url:
        for p in EVIDENCE_SOURCES_DIR.glob("src_*.json"):
            rec = json.loads(p.read_text())
            if rec.get("canonical_url") == canonical_url:
                return rec["id"]
    if content_sha256:
        for p in EVIDENCE_SOURCES_DIR.glob("src_*.json"):
            rec = json.loads(p.read_text())
            if rec.get("content_sha256") == content_sha256:
                return rec["id"]
    return None


def register_segment(
    *,
    source_id: str,
    text: str,
    locator_scheme: str,
    locator_value: str | None = None,
    start: int | None = None,
    end: int | None = None,
) -> str:
    ensure_evidence_dirs()
    seg_id = _uuid7("seg")
    record: dict[str, Any] = {
        "id": seg_id,
        "schema_version": 1,
        "source_id": source_id,
        "text": text,
        "locator": {"scheme": locator_scheme},
        "created_at": _now(),
    }
    if locator_value is not None:
        record["locator"]["value"] = locator_value
    if start is not None:
        record["locator"]["start"] = start
    if end is not None:
        record["locator"]["end"] = end
    EVIDENCE_SEGMENTS_DIR.joinpath(f"{seg_id}.json").write_text(
        json.dumps(record, indent=2)
    )
    return seg_id


def register_claim(
    *,
    statement: str,
    source_ids: list[str],
    claim_status: str = "draft",
    claim_kind: str | None = None,
) -> str:
    ensure_evidence_dirs()
    clm_id = _uuid7("clm")
    record: dict[str, Any] = {
        "id": clm_id,
        "schema_version": 1,
        "statement": statement,
        "claim_status": claim_status,
        "created_at": _now(),
        "source_ids": source_ids,
    }
    if claim_kind:
        record["claim_kind"] = claim_kind
    EVIDENCE_CLAIMS_DIR.joinpath(f"{clm_id}.json").write_text(
        json.dumps(record, indent=2)
    )
    return clm_id


def register_entity(
    *,
    name: str,
    entity_kind: str,
    aliases: list[str] | None = None,
    description: str | None = None,
) -> str:
    ensure_evidence_dirs()
    ent_id = _uuid7("ent")
    record: dict[str, Any] = {
        "id": ent_id,
        "schema_version": 1,
        "name": name,
        "entity_kind": entity_kind,
        "created_at": _now(),
    }
    if aliases:
        record["aliases"] = aliases
    if description:
        record["description"] = description
    EVIDENCE_ENTITIES_DIR.joinpath(f"{ent_id}.json").write_text(
        json.dumps(record, indent=2)
    )
    return ent_id


def register_gap(
    *,
    description: str,
    priority: str = "moderate",
    status: str = "open",
) -> str:
    ensure_evidence_dirs()
    gap_id = _uuid7("gap")
    record: dict[str, Any] = {
        "id": gap_id,
        "schema_version": 1,
        "description": description,
        "priority": priority,
        "status": status,
        "created_at": _now(),
    }
    EVIDENCE_GAPS_DIR.joinpath(f"{gap_id}.json").write_text(
        json.dumps(record, indent=2)
    )
    return gap_id


def register_conflict(
    *,
    claim_ids: list[str],
    severity: str = "high",
    status: str = "open",
) -> str:
    ensure_evidence_dirs()
    cfl_id = _uuid7("cfl")
    record: dict[str, Any] = {
        "id": cfl_id,
        "schema_version": 1,
        "claim_ids": claim_ids,
        "severity": severity,
        "status": status,
        "created_at": _now(),
    }
    EVIDENCE_CONFLICTS_DIR.joinpath(f"{cfl_id}.json").write_text(
        json.dumps(record, indent=2)
    )
    return cfl_id
