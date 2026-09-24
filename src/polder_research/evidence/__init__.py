"""Canonical source, segment, claim, entity, gap, conflict, and evidence-edge records."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..atomic import write_atomic
from ..classification import classify_text, merge_proposals
from ..paths import (
    EVIDENCE_CLAIMS_DIR,
    EVIDENCE_CONFLICTS_DIR,
    EVIDENCE_EDGES_DIR,
    EVIDENCE_ENTITIES_DIR,
    EVIDENCE_GAPS_DIR,
    EVIDENCE_SEGMENTS_DIR,
    EVIDENCE_SOURCES_DIR,
)
from ..schemas import SchemaRegistry

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SENSITIVITY_ORDER = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}


def _classification_policy_metadata(*sources: dict[str, Any]) -> dict[str, Any]:
    """Carry the strictest source privacy labels into derived evidence policy."""
    sensitivity = max(
        (str(source.get("sensitivity", "public")) for source in sources),
        key=lambda value: _SENSITIVITY_ORDER.get(value, 3),
        default="public",
    )
    return {
        "sensitivity": sensitivity,
        "personal_data": any(source.get("personal_data", False) for source in sources),
    }


def _persist(
    target: Path,
    record: dict[str, Any],
    *,
    schema_name: str,
    repository_root: Path | None = None,
    registry_factory: Any = None,
) -> None:
    """Persist one canonical evidence record atomically with schema validation."""
    root = Path(repository_root).resolve() if repository_root is not None else None
    write_atomic(
        target,
        record,
        schema_name=schema_name,
        registry=(
            SchemaRegistry(root)
            if root is not None and (root / "schemas").is_dir()
            else None
        ),
    )


def _classify_record(
    record: dict[str, Any],
    text: str,
    *,
    target_kind: str,
    target_id: str,
    repository_root: Path | None,
    policy_metadata: dict[str, Any],
    output_dir: Path,
) -> None:
    """Run automatic enrichment while leaving a visible failure on evidence."""
    try:
        result = classify_text(
            text,
            target_kind=target_kind,
            target_id=target_id,
            repository_root=repository_root,
            policy_metadata=policy_metadata,
            output_dir=output_dir,
        )
    except (OSError, ValueError, RuntimeError):
        record["classification_status"] = "failed"
        record["classification_error"] = "Classification could not complete; inspect provider configuration and classification records."
        return
    record["classification_status"] = "disabled" if result is None else result["disposition"]
    if result and result.get("disposition") == "failed":
        record["classification_error"] = result.get("error", "Provider classification failed.")
    merge_proposals(record, result)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def assert_record_exists(
    record_id: str,
    *,
    prefix: str,
    default_dir: Path,
    directory_name: str,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    """Verify that a parent record exists on disk and matches its id.

    Writers that take a foreign key (segment.source_id, claim.source_ids,
    conflict.claim_ids, evidence_edge.claim_id/source_id, tasks.acquire_lease)
    call this BEFORE persisting the child. Per AUDIT.md §16: every parent_id
    reference must resolve before the child is written.

    Returns the parsed record so callers can perform additional checks
    (e.g. segment-membership for evidence edges).
    """
    if not isinstance(prefix, str) or not re.fullmatch(r"[a-z]{3}", prefix):
        raise ValueError(f"invalid record prefix: {prefix!r}")
    if not isinstance(record_id, str) or not re.fullmatch(
        rf"{re.escape(prefix)}_[0-9a-f]{{8}}-[0-9a-f]{{4}}-7[0-9a-f]{{3}}-[89ab][0-9a-f]{{3}}-[0-9a-f]{{12}}",
        record_id,
    ):
        raise ValueError(f"invalid {prefix} record id: {record_id!r}")
    path = _record_dir(default_dir, repository_root, directory_name) / f"{record_id}.json"
    if not path.is_file():
        raise ValueError(
            f"parent record does not exist: {record_id!r} (expected under {directory_name}/)"
        )
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("id") != record_id:
        raise ValueError(
            f"parent record identity mismatch: {record_id!r} (file contains {record.get('id')!r})"
        )
    return record


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
    sensitivity: str = "public",
    personal_data: bool = False,
    tags: list[str] | None = None,
    repository_root: Path | None = None,
) -> str:
    """Register a new source record. The content SHA-256 is required (computed
    from ``raw_bytes`` when supplied, otherwise the caller must provide it).
    Persisting an empty hash is forbidden because the canonical schema requires
    a 64-character lowercase SHA-256 (AUDIT.md §32)."""
    if sensitivity not in {"public", "internal", "confidential", "restricted"}:
        raise ValueError("sensitivity must be public, internal, confidential, or restricted")
    if not isinstance(personal_data, bool):
        raise ValueError("personal_data must be a boolean")
    if raw_bytes is not None:
        content_sha256 = compute_content_hash(raw_bytes)
    if not content_sha256 or not isinstance(content_sha256, str):
        raise ValueError(
            "register_source requires a content_sha256 (compute from raw_bytes "
            "or supply it explicitly)"
        )
    if not _SHA256_PATTERN.match(content_sha256):
        raise ValueError(
            f"content_sha256 must be a 64-char lowercase hex string; got {content_sha256!r}"
        )
    ensure_evidence_dirs(repository_root=repository_root)
    sid = _uuid7("src")
    record: dict[str, Any] = {
        "id": sid,
        "schema_version": 1,
        "source_status": "current",
        "source_type": source_type,
        "media_type": media_type,
        "title": title,
        "retrieved_at": _now(),
        "content_sha256": content_sha256,
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
    record["sensitivity"] = sensitivity
    record["personal_data"] = personal_data
    if tags:
        record["tags"] = list(dict.fromkeys(tags))
    try:
        # The registration API receives original bytes, not an extracted text
        # representation. Decode only known text media strictly; PDF, image,
        # audio, video, and unknown payloads are classified from metadata until
        # a format-aware extractor registers locatable text segments.
        text_media = media_type in {"text", "markdown", "html", "json", "csv"}
        text_mime = bool(mime_type and (mime_type.startswith("text/") or mime_type in {
            "application/json", "application/xml", "application/ld+json"
        }))
        text = ""
        if raw_bytes and (text_media or text_mime):
            try:
                text = raw_bytes.decode("utf-8", errors="strict")[:12000]
            except UnicodeDecodeError:
                text = ""
        _classify_record(
            record,
            "\n".join(part for part in (title, source_type, media_type, text) if part),
            target_kind="source",
            target_id=sid,
            repository_root=repository_root,
            policy_metadata={"sensitivity": sensitivity, "personal_data": personal_data},
            output_dir=_record_dir(EVIDENCE_SOURCES_DIR, repository_root, "sources").parent
            / "classifications",
        )
    except (OSError, ValueError, RuntimeError):
        record["classification_status"] = "failed"
        record["classification_error"] = "Classification could not complete; inspect provider configuration and classification records."
    _persist(
        _record_dir(EVIDENCE_SOURCES_DIR, repository_root, "sources").joinpath(f"{sid}.json"),
        record,
        schema_name="source",
        repository_root=repository_root,
    )
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
    source_record = assert_record_exists(
        source_id,
        prefix="src",
        default_dir=EVIDENCE_SOURCES_DIR,
        directory_name="sources",
        repository_root=repository_root,
    )
    ensure_evidence_dirs(repository_root=repository_root)
    seg_id = _uuid7("seg")
    record: dict[str, Any] = {
        "id": seg_id,
        "schema_version": 1,
        "source_id": source_id,
        "text": text,
        "locator": {"scheme": locator_scheme},
        "extracted_at": _now(),
    }
    if locator_value is not None:
        record["locator"]["value"] = locator_value
    if start is not None:
        record["locator"]["start"] = start
    if end is not None:
        record["locator"]["end"] = end
    try:
        _classify_record(
            record, text, target_kind="segment", target_id=seg_id,
            repository_root=repository_root,
            policy_metadata=_classification_policy_metadata(source_record),
            output_dir=_record_dir(EVIDENCE_SEGMENTS_DIR, repository_root, "segments").parent
            / "classifications",
        )
    except (OSError, ValueError, RuntimeError):
        record["classification_status"] = "failed"
        record["classification_error"] = "Classification could not complete; inspect provider configuration and classification records."
    _persist(
        _record_dir(EVIDENCE_SEGMENTS_DIR, repository_root, "segments").joinpath(f"{seg_id}.json"),
        record,
        schema_name="segment",
        repository_root=repository_root,
    )
    return seg_id


def register_claim(
    *,
    statement: str,
    source_ids: list[str],
    claim_status: str = "draft",
    claim_kind: str | None = None,
    tags: list[str] | None = None,
    repository_root: Path | None = None,
) -> str:
    """Register a claim. Every source_id must resolve to an existing source
    record (AUDIT.md §16) before the claim is persisted."""
    if not source_ids:
        raise ValueError("register_claim: source_ids must be a non-empty list")
    source_records = []
    for sid in source_ids:
        source_records.append(assert_record_exists(
            sid,
            prefix="src",
            default_dir=EVIDENCE_SOURCES_DIR,
            directory_name="sources",
            repository_root=repository_root,
        ))
    ensure_evidence_dirs(repository_root=repository_root)
    clm_id = _uuid7("clm")
    record: dict[str, Any] = {
        "id": clm_id,
        "schema_version": 1,
        "statement": statement,
        "claim_status": claim_status,
        "created_at": _now(),
        "source_ids": list(source_ids),
    }
    if claim_kind:
        record["claim_kind"] = claim_kind
    if tags:
        record["tags"] = list(dict.fromkeys(tags))
    try:
        _classify_record(
            record, statement, target_kind="claim", target_id=clm_id,
            repository_root=repository_root,
            policy_metadata=_classification_policy_metadata(*source_records),
            output_dir=_record_dir(EVIDENCE_CLAIMS_DIR, repository_root, "claims").parent
            / "classifications",
        )
    except (OSError, ValueError, RuntimeError):
        record["classification_status"] = "failed"
        record["classification_error"] = "Classification could not complete; inspect provider configuration and classification records."
    _persist(
        _record_dir(EVIDENCE_CLAIMS_DIR, repository_root, "claims").joinpath(f"{clm_id}.json"),
        record,
        schema_name="claim",
        repository_root=repository_root,
    )
    return clm_id


def register_entity(
    *,
    name: str,
    entity_kind: str,
    aliases: list[str] | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    source_ids: list[str] | None = None,
    repository_root: Path | None = None,
) -> str:
    source_records = [
        assert_record_exists(
            source_id,
            prefix="src",
            default_dir=EVIDENCE_SOURCES_DIR,
            directory_name="sources",
            repository_root=repository_root,
        )
        for source_id in dict.fromkeys(source_ids or [])
    ]
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
    if tags:
        record["tags"] = list(dict.fromkeys(tags))
    if source_ids:
        record["source_ids"] = list(dict.fromkeys(source_ids))
    try:
        _classify_record(
            record,
            "\n".join(part for part in (name, description or "", " ".join(aliases or [])) if part),
            target_kind="entity", target_id=ent_id, repository_root=repository_root,
            policy_metadata={
                **_classification_policy_metadata(*source_records),
                "personal_data": entity_kind == "person"
                or any(source.get("personal_data", False) for source in source_records),
            },
            output_dir=_record_dir(EVIDENCE_ENTITIES_DIR, repository_root, "entities").parent
            / "classifications",
        )
    except (OSError, ValueError, RuntimeError):
        record["classification_status"] = "failed"
        record["classification_error"] = "Classification could not complete; inspect provider configuration and classification records."
    _persist(
        _record_dir(EVIDENCE_ENTITIES_DIR, repository_root, "entities").joinpath(f"{ent_id}.json"),
        record,
        schema_name="entity",
        repository_root=repository_root,
    )
    return ent_id


def register_gap(
    *,
    description: str,
    priority: str = "medium",
    status: str = "open",
    repository_root: Path | None = None,
) -> str:
    """Create a gap record. Priority defaults to ``medium`` (canonical)."""
    canonical_priorities = ("low", "medium", "high", "critical")
    status_values = (
        "open",
        "investigating",
        "filled",
        "deferred",
        "wontfix",
    )
    if priority not in canonical_priorities:
        raise ValueError(f"gap priority {priority!r} is not one of {canonical_priorities!r}")
    if status not in status_values:
        raise ValueError(f"gap status {status!r} is not one of {status_values!r}")
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
    _persist(
        _record_dir(EVIDENCE_GAPS_DIR, repository_root, "gaps").joinpath(f"{gap_id}.json"),
        record,
        schema_name="gap",
        repository_root=repository_root,
    )
    return gap_id


def register_conflict(
    *,
    claim_ids: list[str],
    severity: str = "high",
    status: str = "open",
    repository_root: Path | None = None,
) -> str:
    """Register a conflict. Every claim_id must resolve to an existing claim
    record (AUDIT.md §16) before the conflict is persisted. Conflicts must
    contain at least two distinct claims."""
    if len(claim_ids) < 2:
        raise ValueError("register_conflict: claim_ids must reference at least two claims")
    if len(set(claim_ids)) != len(claim_ids):
        raise ValueError("register_conflict: claim_ids must be unique")
    for cid in claim_ids:
        assert_record_exists(
            cid,
            prefix="clm",
            default_dir=EVIDENCE_CLAIMS_DIR,
            directory_name="claims",
            repository_root=repository_root,
        )
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
    _persist(
        _record_dir(EVIDENCE_CONFLICTS_DIR, repository_root, "conflicts").joinpath(
            f"{cfl_id}.json"
        ),
        record,
        schema_name="conflict",
        repository_root=repository_root,
    )
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

    assert_record_exists(
        claim_id,
        prefix="clm",
        default_dir=EVIDENCE_CLAIMS_DIR,
        directory_name="claims",
        repository_root=repository_root,
    )
    assert_record_exists(
        source_id,
        prefix="src",
        default_dir=EVIDENCE_SOURCES_DIR,
        directory_name="sources",
        repository_root=repository_root,
    )

    edge_locator: dict[str, str]
    if segment_id is not None:
        segment = assert_record_exists(
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
    _persist(
        _record_dir(EVIDENCE_EDGES_DIR, repository_root, "edges").joinpath(f"{edge_id}.json"),
        record,
        schema_name="evidence",
        repository_root=repository_root,
    )
    return edge_id
