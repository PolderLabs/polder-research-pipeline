"""Canonical source, segment, claim, entity, gap, conflict, and evidence-edge records."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..paths import (
    EVIDENCE_CLAIMS_DIR,
    EVIDENCE_CONFLICTS_DIR,
    EVIDENCE_EDGES_DIR,
    EVIDENCE_ENTITIES_DIR,
    EVIDENCE_GAPS_DIR,
    EVIDENCE_SEGMENTS_DIR,
    EVIDENCE_SOURCES_DIR,
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def _record_dir(default: Path, repository_root: Path | None, name: str) -> Path:
    if repository_root is None:
        return default
    return Path(repository_root) / ".research" / name


def compute_content_hash(content: bytes | Path) -> str:
    """Compute SHA-256 of raw bytes or a file."""
    if isinstance(content, Path):
        content = content.read_bytes()
    return hashlib.sha256(content).hexdigest()


def ensure_evidence_dirs(*, repository_root: Path | None = None) -> None:
    """Create all evidence subdirectories under ``.research``."""
    for default, name in (
        (EVIDENCE_SOURCES_DIR, "sources"),
        (EVIDENCE_CLAIMS_DIR, "claims"),
        (EVIDENCE_ENTITIES_DIR, "entities"),
        (EVIDENCE_SEGMENTS_DIR, "segments"),
        (EVIDENCE_GAPS_DIR, "gaps"),
        (EVIDENCE_CONFLICTS_DIR, "conflicts"),
        (EVIDENCE_EDGES_DIR, "edges"),
    ):
        _record_dir(default, repository_root, name).mkdir(parents=True, exist_ok=True)


def register_source(
    *,
    title: str,
    source_type: str,
    media_type: str,
    raw_bytes: bytes | None = None,
    doi: str | None = None,
    canonical_url: str | None = None,
    content_sha256: str | None = None,
    raw_location: str | None = None,
    byte_size: int | None = None,
    mime_type: str | None = None,
    repository_root: Path | None = None,
) -> str:
    """Register a new source record, compute content hash if raw_bytes provided."""
    ensure_evidence_dirs(repository_root=repository_root)
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
    if raw_location:
        record["raw_location"] = raw_location
    if byte_size is not None:
        record["byte_size"] = byte_size
    if mime_type:
        record["mime_type"] = mime_type
    _record_dir(EVIDENCE_SOURCES_DIR, repository_root, "sources").joinpath(
        f"{sid}.json"
    ).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return sid


def find_duplicate_source(
    *,
    doi: str | None = None,
    canonical_url: str | None = None,
    content_sha256: str | None = None,
    raw_location: str | None = None,
    repository_root: Path | None = None,
) -> str | None:
    """Find an existing source by stable identity, strongest signal first."""
    source_dir = _record_dir(EVIDENCE_SOURCES_DIR, repository_root, "sources")
    checks = (
        ("doi", doi),
        ("canonical_url", canonical_url),
        ("content_sha256", content_sha256),
        ("raw_location", raw_location),
    )
    for field, expected in checks:
        if not expected:
            continue
        for path in source_dir.glob("src_*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get(field) == expected:
                return record["id"]
    return None


def register_segment(
    *,
    source_id: str,
    text: str,
    locator_scheme: str,
    locator_value: str | None = None,
    start: str | None = None,
    end: str | None = None,
    repository_root: Path | None = None,
) -> str:
    ensure_evidence_dirs(repository_root=repository_root)
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
    _record_dir(EVIDENCE_SEGMENTS_DIR, repository_root, "segments").joinpath(
        f"{seg_id}.json"
    ).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return seg_id


def register_claim(
    *,
    statement: str,
    source_ids: list[str],
    claim_status: str = "draft",
    claim_kind: str | None = None,
    repository_root: Path | None = None,
) -> str:
    ensure_evidence_dirs(repository_root=repository_root)
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
    _record_dir(EVIDENCE_CLAIMS_DIR, repository_root, "claims").joinpath(
        f"{clm_id}.json"
    ).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return clm_id


def register_entity(
    *,
    name: str,
    entity_kind: str,
    aliases: list[str] | None = None,
    description: str | None = None,
    repository_root: Path | None = None,
) -> str:
    ensure_evidence_dirs(repository_root=repository_root)
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
    _record_dir(EVIDENCE_ENTITIES_DIR, repository_root, "entities").joinpath(
        f"{ent_id}.json"
    ).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return ent_id


def register_gap(
    *,
    description: str,
    priority: str = "moderate",
    status: str = "open",
    repository_root: Path | None = None,
) -> str:
    ensure_evidence_dirs(repository_root=repository_root)
    gap_id = _uuid7("gap")
    record: dict[str, Any] = {
        "id": gap_id,
        "schema_version": 1,
        "description": description,
        "priority": priority,
        "status": status,
        "created_at": _now(),
    }
    _record_dir(EVIDENCE_GAPS_DIR, repository_root, "gaps").joinpath(f"{gap_id}.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    return gap_id


def register_conflict(
    *,
    claim_ids: list[str],
    severity: str = "high",
    status: str = "open",
    repository_root: Path | None = None,
) -> str:
    ensure_evidence_dirs(repository_root=repository_root)
    cfl_id = _uuid7("cfl")
    record: dict[str, Any] = {
        "id": cfl_id,
        "schema_version": 1,
        "claim_ids": claim_ids,
        "severity": severity,
        "status": status,
        "created_at": _now(),
    }
    _record_dir(EVIDENCE_CONFLICTS_DIR, repository_root, "conflicts").joinpath(
        f"{cfl_id}.json"
    ).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return cfl_id


EVIDENCE_RELATIONS = frozenset(
    {
        "supports",
        "contradicts",
        "partially-supports",
        "qualifies",
        "contextualizes",
        "updates",
        "supersedes",
    }
)


def _require_record(
    record_id: str,
    *,
    prefix: str,
    default_dir: Path,
    directory_name: str,
    repository_root: Path | None,
) -> dict[str, Any]:
    if not record_id.startswith(f"{prefix}_"):
        raise ValueError(f"expected {prefix}_ record id, got {record_id!r}")
    path = _record_dir(default_dir, repository_root, directory_name) / f"{record_id}.json"
    if not path.is_file():
        raise ValueError(f"record does not exist: {record_id}")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("id") != record_id:
        raise ValueError(f"record identity mismatch: {record_id}")
    return record


def register_evidence_edge(
    *,
    claim_id: str,
    source_id: str,
    relation: str,
    segment_id: str | None = None,
    locator: Mapping[str, str] | None = None,
    directness: str = "unknown",
    confidence: str = "medium",
    repository_root: Path | None = None,
) -> str:
    """Connect an existing claim to an existing source or exact source segment.

    The referenced records are resolved before the edge is written.  A segment
    must belong to ``source_id``; source-level edges must carry an explicit
    locator rather than pretending that extraction occurred.
    """
    if relation not in EVIDENCE_RELATIONS:
        raise ValueError(f"invalid evidence relation: {relation!r}")
    if directness not in {"primary", "secondary", "tertiary", "unknown"}:
        raise ValueError(f"invalid evidence directness: {directness!r}")
    if confidence not in {"high", "medium", "low"}:
        raise ValueError(f"invalid evidence confidence: {confidence!r}")

    _require_record(
        claim_id,
        prefix="clm",
        default_dir=EVIDENCE_CLAIMS_DIR,
        directory_name="claims",
        repository_root=repository_root,
    )
    _require_record(
        source_id,
        prefix="src",
        default_dir=EVIDENCE_SOURCES_DIR,
        directory_name="sources",
        repository_root=repository_root,
    )

    edge_locator: dict[str, str]
    if segment_id is not None:
        segment = _require_record(
            segment_id,
            prefix="seg",
            default_dir=EVIDENCE_SEGMENTS_DIR,
            directory_name="segments",
            repository_root=repository_root,
        )
        if segment.get("source_id") != source_id:
            raise ValueError(f"segment {segment_id} does not belong to {source_id}")
        edge_locator = dict(segment.get("locator", {}))
    elif locator is not None:
        edge_locator = dict(locator)
    else:
        raise ValueError("evidence edge requires segment_id or locator")

    if edge_locator.get("scheme") not in {
        "page",
        "section",
        "paragraph",
        "line",
        "timestamp",
        "chapter",
        "anchor",
        "byte-offset",
        "sha256",
    }:
        raise ValueError("evidence locator requires a valid scheme")

    ensure_evidence_dirs(repository_root=repository_root)
    edge_id = _uuid7("evd")
    record: dict[str, Any] = {
        "id": edge_id,
        "schema_version": 1,
        "claim_id": claim_id,
        "source_id": source_id,
        "relation": relation,
        "directness": directness,
        "confidence": confidence,
        "locator": edge_locator,
        "created_at": _now(),
    }
    if segment_id is not None:
        record["segment_id"] = segment_id
    _record_dir(EVIDENCE_EDGES_DIR, repository_root, "edges").joinpath(
        f"{edge_id}.json"
    ).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return edge_id
