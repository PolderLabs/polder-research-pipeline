"""Protocol-first records for auditable systematic evidence reviews.

This module keeps database search hits separate from acquired ``source`` records.
Review decisions and appraisals are append-only records; the flow summary and
completion checks are derived from those records rather than hand-entered counts.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..atomic import write_atomic
from ..evidence import assert_record_exists
from ..paths import (
    EVIDENCE_CLAIMS_DIR,
    EVIDENCE_CONFLICTS_DIR,
    EVIDENCE_SEGMENTS_DIR,
    EVIDENCE_SOURCES_DIR,
    REPO_ROOT,
    RESEARCH_APPRAISALS_DIR,
    RESEARCH_CANDIDATES_DIR,
    RESEARCH_EXTRACTIONS_DIR,
    RESEARCH_PROTOCOLS_DIR,
    RESEARCH_REPORTS_DIR,
    RESEARCH_RUNS_DIR,
    RESEARCH_SCREENINGS_DIR,
    RESEARCH_SEARCHES_DIR,
    Workspace,
    active_workspace,
    resolve_workspace,
    workspace_path,
    workspace_scoped,
)
from ..schemas import SchemaError, validate
from ..urls import normalize_url


class ResearchMethodError(ValueError):
    """A method record violates its protocol or cross-record invariants."""


_ID_PATTERN = re.compile(
    r"^(?P<prefix>[a-z]{3})_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _require_id(record_id: str, prefix: str) -> None:
    if (
        not isinstance(record_id, str)
        or not _ID_PATTERN.fullmatch(record_id)
        or not record_id.startswith(f"{prefix}_")
    ):
        raise ResearchMethodError(f"invalid {prefix} record ID: {record_id!r}")


def _require_timestamp(value: str, field: str) -> datetime:
    if not isinstance(value, str):
        raise ResearchMethodError(f"{field} must be a timezone-aware ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResearchMethodError(f"{field} must be a timezone-aware ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ResearchMethodError(f"{field} must include a timezone")
    return parsed


def _export_path(location: str, workspace: Workspace | Path | str | None = None) -> Path:
    selected = workspace if workspace is not None else active_workspace()
    root = resolve_workspace(selected).root if selected is not None else REPO_ROOT
    path = Path(location)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ResearchMethodError("search exports must be stored inside the workspace") from exc
    return resolved


def _verify_export(
    location: str,
    expected_sha256: str,
    workspace: Workspace | Path | str | None = None,
) -> None:
    path = _export_path(location, workspace)
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ResearchMethodError(f"cannot read saved search export {path}: {exc}") from exc
    if actual != expected_sha256:
        raise ResearchMethodError(f"saved search export hash mismatch: {path}")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _uuid7(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid7()}"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ResearchMethodError(f"cannot read record {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResearchMethodError(f"record {path} must contain a JSON object")
    return value


def _record(directory: Path, record_id: str) -> dict[str, Any]:
    expected_prefix = {
        "runs": "run",
        "protocols": "prm",
        "searches": "sea",
        "candidates": "can",
        "screenings": "scr",
        "appraisals": "app",
        "extractions": "ext",
    }.get(directory.name)
    if expected_prefix:
        _require_id(record_id, expected_prefix)
    record = _read(directory / f"{record_id}.json")
    schema_name = {
        "runs": "run",
        "protocols": "protocol",
        "searches": "search",
        "candidates": "candidate",
        "screenings": "screening",
        "appraisals": "appraisal",
        "extractions": "extraction",
    }.get(directory.name)
    if schema_name:
        try:
            validate(schema_name, record)
        except SchemaError as exc:
            raise ResearchMethodError(f"invalid {schema_name} record {record_id}: {exc}") from exc
    if record.get("id") != record_id:
        raise ResearchMethodError(f"record identity mismatch for {record_id!r}")
    return record


def _records(directory: Path, prefix: str, run_id: str) -> list[dict[str, Any]]:
    records = []
    schema_name = {
        "sea_": "search",
        "can_": "candidate",
        "scr_": "screening",
        "app_": "appraisal",
        "ext_": "extraction",
    }[prefix]
    for path in sorted(directory.glob(f"{prefix}*.json")):
        record = _read(path)
        if record.get("id") != path.stem:
            raise ResearchMethodError(f"record identity mismatch in {path}")
        try:
            validate(schema_name, record)
        except SchemaError as exc:
            raise ResearchMethodError(f"invalid {schema_name} record in {path}: {exc}") from exc
        if record.get("run_id") == run_id:
            records.append(record)
    return records


def _protocol_content_hash(protocol: dict[str, Any]) -> str:
    content = {
        key: value
        for key, value in protocol.items()
        if key not in {"status", "frozen_at", "content_sha256"}
    }
    payload = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _run(run_id: str) -> dict[str, Any]:
    run = _record(workspace_path(RESEARCH_RUNS_DIR), run_id)
    if run.get("id") != run_id:
        raise ResearchMethodError(f"run identity mismatch for {run_id!r}")
    return run


def _require_acquired_source(source_id: str) -> dict[str, Any]:
    source = assert_record_exists(
        source_id,
        prefix="src",
        default_dir=workspace_path(EVIDENCE_SOURCES_DIR),
        directory_name="sources",
    )
    if (
        source.get(
            "acquisition_status",
            "unacquired" if source.get("source_status") == "unacquired" else "acquired",
        )
        == "unacquired"
    ):
        raise ResearchMethodError(f"source {source_id} must be acquired before this operation")
    return source


def _frozen_for_run(
    run_id: str, *, require_active: bool = True
) -> tuple[dict[str, Any], dict[str, Any]]:
    run = _run(run_id)
    if run.get("research_method") != "systematic_evidence_review":
        raise ResearchMethodError(f"run {run_id} is not a systematic evidence review")
    if require_active and run.get("run_status") != "active":
        raise ResearchMethodError(f"run {run_id} must be active for this operation")
    protocol_id = run.get("protocol_id")
    if not protocol_id:
        raise ResearchMethodError(f"run {run_id} has no frozen protocol")
    protocol = _record(workspace_path(RESEARCH_PROTOCOLS_DIR), protocol_id)
    if protocol.get("id") != protocol_id or protocol.get("run_id") != run_id:
        raise ResearchMethodError("protocol identity or run reference does not match")
    if protocol.get("status") != "frozen":
        raise ResearchMethodError(f"protocol {protocol_id} is not frozen")
    digest = _protocol_content_hash(protocol)
    if protocol.get("content_sha256") != digest or run.get("protocol_sha256") != digest:
        raise ResearchMethodError(f"frozen protocol hash mismatch for run {run_id}")
    return run, protocol


@workspace_scoped
def create_protocol(
    run_id: str,
    protocol: dict[str, Any],
    *,
    created_by: str,
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Create a draft protocol for a draft systematic-review run."""
    run = _run(run_id)
    if run.get("research_method") != "systematic_evidence_review":
        raise ResearchMethodError("protocols are only valid for systematic evidence reviews")
    if run.get("run_status") != "draft" or run.get("protocol_id"):
        raise ResearchMethodError("a protocol can only be created once on a draft run")
    record = dict(protocol)
    record.update(
        {
            "id": _uuid7("prm"),
            "schema_version": 1,
            "run_id": run_id,
            "research_method": "systematic_evidence_review",
            "status": "draft",
            "created_at": _now(),
            "created_by": created_by,
        }
    )
    try:
        validate("protocol", record)
    except SchemaError as exc:
        raise ResearchMethodError(str(exc)) from exc
    _require_timestamp(record["search_plan"]["cutoff_at"], "protocol.search_plan.cutoff_at")
    screening = record["screening_plan"]
    reviewers = screening["reviewers"]
    reviewer_ids = [reviewer["id"] for reviewer in reviewers]
    human_groups = {
        reviewer["independence_group"] for reviewer in reviewers if reviewer["kind"] == "human"
    }
    if len(reviewer_ids) != len(set(reviewer_ids)):
        raise ResearchMethodError("screening reviewer IDs must be unique")
    if len(human_groups) < 2:
        raise ResearchMethodError("systematic screening requires two independent human reviewers")
    if screening["adjudicator"]["id"] in reviewer_ids:
        raise ResearchMethodError("the adjudicator must be independent of the screeners")
    query_ids = [query["id"] for query in record["search_plan"]["queries"]]
    if len(query_ids) != len(set(query_ids)):
        raise ResearchMethodError("protocol query IDs must be unique")
    if record["question"].strip() != run.get("brief", {}).get("question", "").strip():
        raise ResearchMethodError("protocol question must match the run brief question")
    write_atomic(
        workspace_path(RESEARCH_PROTOCOLS_DIR) / f"{record['id']}.json",
        record,
        schema_name="protocol",
    )
    return record["id"]


@workspace_scoped
def freeze_protocol(protocol_id: str, *, workspace: Workspace | Path | str | None = None) -> str:
    """Freeze a draft protocol and bind its digest to the run before activation."""
    protocol = _record(workspace_path(RESEARCH_PROTOCOLS_DIR), protocol_id)
    run_id = protocol.get("run_id")
    if not isinstance(run_id, str):
        raise ResearchMethodError("protocol has no run_id")
    run = _run(run_id)
    if run.get("run_status") != "draft":
        raise ResearchMethodError("a protocol can only be frozen before run activation")
    if protocol.get("status") == "frozen":
        if protocol.get("content_sha256") != _protocol_content_hash(protocol):
            raise ResearchMethodError("frozen protocol was modified")
        digest = protocol["content_sha256"]
    else:
        protocol["status"] = "frozen"
        protocol["frozen_at"] = _now()
        digest = _protocol_content_hash(protocol)
        protocol["content_sha256"] = digest
        write_atomic(
            workspace_path(RESEARCH_PROTOCOLS_DIR) / f"{protocol_id}.json",
            protocol,
            schema_name="protocol",
        )
    run["protocol_id"] = protocol_id
    run["protocol_sha256"] = digest
    write_atomic(workspace_path(RESEARCH_RUNS_DIR) / f"{run_id}.json", run, schema_name="run")
    return digest


@workspace_scoped
def verify_run_protocol(
    run_id: str, *, workspace: Workspace | Path | str | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Check the frozen protocol binding; used by run lifecycle transitions."""
    return _frozen_for_run(run_id, require_active=False)


@workspace_scoped
def record_search(
    run_id: str,
    *,
    query_id: str,
    executed_by: str,
    executed_at: str,
    result_count: int,
    export_sha256: str | None = None,
    export_location: str | None = None,
    tool_name: str = "",
    tool_version: str = "",
    notes: str = "",
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Record a search exactly as prespecified in the frozen protocol."""
    _, protocol = _frozen_for_run(run_id)
    planned = next(
        (query for query in protocol["search_plan"]["queries"] if query["id"] == query_id), None
    )
    if planned is None:
        raise ResearchMethodError(f"query {query_id!r} is not in the frozen protocol")
    _require_timestamp(executed_at, "search.executed_at")
    if result_count > 0 and (export_sha256 is None or export_location is None):
        raise ResearchMethodError(
            "nonempty search results require a preserved export location and hash"
        )
    if (export_sha256 is None) != (export_location is None):
        raise ResearchMethodError("search export location and hash must be provided together")
    if export_location and export_sha256:
        _verify_export(export_location, export_sha256)
    record: dict[str, Any] = {
        "id": _uuid7("sea"),
        "schema_version": 1,
        "run_id": run_id,
        "protocol_id": protocol["id"],
        "protocol_sha256": protocol["content_sha256"],
        "query_id": query_id,
        "database": planned["database"],
        "platform": planned["platform"],
        "query": planned["query"],
        "executed_at": executed_at,
        "executed_by": executed_by,
        "result_count": result_count,
        "tool_name": tool_name,
        "tool_version": tool_version,
        "notes": notes,
        "parameters": {
            key: planned[key]
            for key in ("date_from", "date_to", "language", "limits")
            if key in planned
        },
    }
    if export_sha256 is not None:
        record["export_sha256"] = export_sha256
    if export_location is not None:
        record["export_location"] = export_location
    write_atomic(
        workspace_path(RESEARCH_SEARCHES_DIR) / f"{record['id']}.json", record, schema_name="search"
    )
    return record["id"]


def _dedupe_key(title: str, identifiers: list[str], url: str | None) -> str:
    for identifier in identifiers:
        value = identifier.strip().lower()
        if value:
            if value.startswith("doi:"):
                value = value[4:]
            return hashlib.sha256(f"id:{value}".encode()).hexdigest()
    if url:
        normalized = normalize_url(url)
        if normalized:
            return hashlib.sha256(f"url:{normalized}".encode()).hexdigest()
    normalized_title = re.sub(r"\s+", " ", title).strip().casefold()
    return hashlib.sha256(f"title:{normalized_title}".encode()).hexdigest()


@workspace_scoped
def register_candidate(
    run_id: str,
    *,
    search_id: str,
    title: str,
    stable_identifiers: list[str] | None = None,
    authors: list[str] | None = None,
    published_at: str = "",
    url: str | None = None,
    abstract: str = "",
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Record one returned search hit; duplicates remain explicit candidates."""
    _, protocol = _frozen_for_run(run_id)
    search = _record(workspace_path(RESEARCH_SEARCHES_DIR), search_id)
    if (
        search.get("run_id") != run_id
        or search.get("protocol_sha256") != protocol["content_sha256"]
    ):
        raise ResearchMethodError("search does not belong to this run's frozen protocol")
    identifiers = list(stable_identifiers or [])
    key = _dedupe_key(title, identifiers, url)
    duplicates = [
        candidate
        for candidate in _records(workspace_path(RESEARCH_CANDIDATES_DIR), "can_", run_id)
        if candidate.get("dedupe_key") == key
    ]
    canonical = next(
        (candidate for candidate in duplicates if candidate.get("status") == "unique"), None
    )
    record: dict[str, Any] = {
        "id": _uuid7("can"),
        "schema_version": 1,
        "run_id": run_id,
        "protocol_id": protocol["id"],
        "protocol_sha256": protocol["content_sha256"],
        "search_ids": [search_id],
        "stable_identifiers": identifiers,
        "title": title,
        "authors": list(authors or []),
        "published_at": published_at,
        "dedupe_key": key,
        "status": "duplicate" if canonical else "unique",
        "discovered_at": _now(),
    }
    if url:
        record["url"] = url
    if abstract:
        record["abstract"] = abstract
    if canonical:
        record["duplicate_of"] = canonical["id"]
    write_atomic(
        workspace_path(RESEARCH_CANDIDATES_DIR) / f"{record['id']}.json",
        record,
        schema_name="candidate",
    )
    return record["id"]


@workspace_scoped
def record_screening_decision(
    run_id: str,
    *,
    candidate_id: str,
    stage: str,
    reviewer_id: str,
    outcome: str,
    rationale: str,
    exclusion_reason: str | None = None,
    source_id: str | None = None,
    decided_at: str | None = None,
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Append a prespecified independent human screening decision."""
    _, protocol = _frozen_for_run(run_id)
    candidate = _record(workspace_path(RESEARCH_CANDIDATES_DIR), candidate_id)
    if candidate.get("run_id") != run_id or candidate.get("status") != "unique":
        raise ResearchMethodError("screening requires a unique candidate from this run")
    reviewers = {item["id"]: item for item in protocol["screening_plan"]["reviewers"]}
    reviewer = reviewers.get(reviewer_id)
    if reviewer is None or reviewer["kind"] != "human":
        raise ResearchMethodError(
            "systematic screening decisions must use a protocol-listed human reviewer"
        )
    if stage not in {"title_abstract", "full_text"}:
        raise ResearchMethodError(f"invalid screening stage {stage!r}")
    if outcome not in {"include", "exclude", "uncertain"}:
        raise ResearchMethodError(f"invalid screening outcome {outcome!r}")
    if stage == "full_text":
        prior = [
            decision
            for decision in _records(workspace_path(RESEARCH_SCREENINGS_DIR), "scr_", run_id)
            if decision.get("candidate_id") == candidate_id
            and decision.get("stage") == "title_abstract"
        ]
        if _final_decision(prior) != "include":
            raise ResearchMethodError(
                "full-text screening requires resolved title/abstract inclusion"
            )
    if stage == "full_text" and outcome == "include" and not source_id:
        raise ResearchMethodError("full-text inclusion requires an acquired source_id")
    if stage == "full_text" and outcome == "include" and source_id:
        _require_acquired_source(source_id)
    if source_id:
        _require_id(source_id, "src")
        if not (stage == "full_text" and outcome == "include"):
            assert_record_exists(
                source_id,
                prefix="src",
                default_dir=workspace_path(EVIDENCE_SOURCES_DIR),
                directory_name="sources",
            )
    if outcome == "exclude" and not exclusion_reason:
        raise ResearchMethodError("excluded records require a prespecified exclusion reason")
    if exclusion_reason and exclusion_reason not in protocol["screening_plan"]["exclusion_reasons"]:
        raise ResearchMethodError("exclusion reason is not in the frozen protocol")
    _require_timestamp(decided_at or _now(), "screening.decided_at")
    for existing in _records(workspace_path(RESEARCH_SCREENINGS_DIR), "scr_", run_id):
        if (
            existing.get("run_id"),
            existing.get("candidate_id"),
            existing.get("stage"),
            existing.get("decision_kind"),
            existing.get("reviewer_id"),
        ) == (run_id, candidate_id, stage, "independent", reviewer_id):
            raise ResearchMethodError("reviewer has already screened this candidate at this stage")
    record: dict[str, Any] = {
        "id": _uuid7("scr"),
        "schema_version": 1,
        "run_id": run_id,
        "protocol_id": protocol["id"],
        "protocol_sha256": protocol["content_sha256"],
        "candidate_id": candidate_id,
        "stage": stage,
        "decision_kind": "independent",
        "reviewer_id": reviewer_id,
        "outcome": outcome,
        "rationale": rationale,
        "decided_at": decided_at or _now(),
    }
    if exclusion_reason:
        record["exclusion_reason"] = exclusion_reason
    if source_id:
        record["source_id"] = source_id
    write_atomic(
        workspace_path(RESEARCH_SCREENINGS_DIR) / f"{record['id']}.json",
        record,
        schema_name="screening",
    )
    return record["id"]


@workspace_scoped
def adjudicate_screening(
    run_id: str,
    *,
    candidate_id: str,
    stage: str,
    outcome: str,
    adjudicator_id: str,
    rationale: str,
    exclusion_reason: str | None = None,
    source_id: str | None = None,
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Append an adjudication only when two independent decisions disagree."""
    _, protocol = _frozen_for_run(run_id)
    screening_plan = protocol["screening_plan"]
    if adjudicator_id != screening_plan["adjudicator"]["id"]:
        raise ResearchMethodError("adjudicator does not match the frozen protocol")
    candidate = _record(workspace_path(RESEARCH_CANDIDATES_DIR), candidate_id)
    if candidate.get("run_id") != run_id or candidate.get("status") != "unique":
        raise ResearchMethodError("adjudication requires a unique candidate from this run")
    if stage not in {"title_abstract", "full_text"} or outcome not in {
        "include",
        "exclude",
        "uncertain",
    }:
        raise ResearchMethodError("invalid adjudication stage or outcome")
    decisions = [
        _read(path)
        for path in sorted(workspace_path(RESEARCH_SCREENINGS_DIR).glob("scr_*.json"))
        if (decision := _read(path)).get("run_id") == run_id
        and decision.get("candidate_id") == candidate_id
        and decision.get("stage") == stage
        and decision.get("decision_kind") == "independent"
    ]
    if len(decisions) < 2 or len({item["outcome"] for item in decisions}) == 1:
        raise ResearchMethodError("adjudication requires disagreeing independent decisions")
    prior_records = [
        _read(path)
        for path in workspace_path(RESEARCH_SCREENINGS_DIR).glob("scr_*.json")
        if (item := _read(path)).get("run_id") == run_id
        and item.get("candidate_id") == candidate_id
        and item.get("stage") == stage
    ]
    if any(item.get("decision_kind") == "adjudication" for item in prior_records):
        raise ResearchMethodError("this candidate stage already has an adjudication")
    if outcome == "exclude" and not exclusion_reason:
        raise ResearchMethodError("adjudicated exclusions require an exclusion reason")
    if exclusion_reason and exclusion_reason not in screening_plan["exclusion_reasons"]:
        raise ResearchMethodError("adjudicated exclusion reason is not in the frozen protocol")
    if stage == "full_text" and outcome == "include" and not source_id:
        raise ResearchMethodError("full-text adjudication inclusion requires an acquired source_id")
    if stage == "full_text" and outcome == "include" and source_id:
        _require_acquired_source(source_id)
    if source_id:
        _require_id(source_id, "src")
        if not (stage == "full_text" and outcome == "include"):
            assert_record_exists(
                source_id,
                prefix="src",
                default_dir=workspace_path(EVIDENCE_SOURCES_DIR),
                directory_name="sources",
            )
    record: dict[str, Any] = {
        "id": _uuid7("scr"),
        "schema_version": 1,
        "run_id": run_id,
        "protocol_id": protocol["id"],
        "protocol_sha256": protocol["content_sha256"],
        "candidate_id": candidate_id,
        "stage": stage,
        "decision_kind": "adjudication",
        "reviewer_id": adjudicator_id,
        "outcome": outcome,
        "rationale": rationale,
        "resolves_decision_ids": sorted(item["id"] for item in decisions),
        "decided_at": _now(),
    }
    if exclusion_reason:
        record["exclusion_reason"] = exclusion_reason
    if source_id:
        record["source_id"] = source_id
    write_atomic(
        workspace_path(RESEARCH_SCREENINGS_DIR) / f"{record['id']}.json",
        record,
        schema_name="screening",
    )
    return record["id"]


@workspace_scoped
def record_appraisal(
    run_id: str,
    *,
    candidate_id: str,
    source_id: str,
    reviewer_id: str,
    instrument: str,
    overall_judgement: str,
    domains: list[dict[str, str]],
    limitations: list[str] | None = None,
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Record domain-level critical appraisal without collapsing it to a score."""
    _, protocol = _frozen_for_run(run_id)
    candidate = _record(workspace_path(RESEARCH_CANDIDATES_DIR), candidate_id)
    if candidate.get("run_id") != run_id or candidate.get("status") != "unique":
        raise ResearchMethodError("appraisal candidate does not belong to this run")
    _require_id(source_id, "src")
    _require_acquired_source(source_id)
    if instrument != protocol["appraisal_plan"]["instrument"]:
        raise ResearchMethodError("appraisal instrument does not match the frozen protocol")
    instrument_version = protocol["appraisal_plan"]["instrument_version"]
    instrument_reference = protocol["appraisal_plan"]["instrument_reference"]
    reviewer = next(
        (r for r in protocol["screening_plan"]["reviewers"] if r["id"] == reviewer_id), None
    )
    if reviewer is None or reviewer["kind"] != "human":
        raise ResearchMethodError("appraisal reviewer must be a protocol-listed human reviewer")
    full_text_decisions = [
        item
        for item in _records(workspace_path(RESEARCH_SCREENINGS_DIR), "scr_", run_id)
        if item.get("candidate_id") == candidate_id and item.get("stage") == "full_text"
    ]
    if _final_decision(full_text_decisions) != "include":
        raise ResearchMethodError("appraisal requires a resolved full-text inclusion")
    if source_id not in {item.get("source_id") for item in full_text_decisions}:
        raise ResearchMethodError(
            "appraised source is not linked by the full-text screening decision"
        )
    record = {
        "id": _uuid7("app"),
        "schema_version": 1,
        "run_id": run_id,
        "protocol_id": protocol["id"],
        "protocol_sha256": protocol["content_sha256"],
        "candidate_id": candidate_id,
        "source_id": source_id,
        "reviewer_id": reviewer_id,
        "instrument": instrument,
        "instrument_version": instrument_version,
        "instrument_reference": instrument_reference,
        "overall_judgement": overall_judgement,
        "domains": domains,
        "limitations": list(limitations or []),
        "completed_at": _now(),
    }
    write_atomic(
        workspace_path(RESEARCH_APPRAISALS_DIR) / f"{record['id']}.json",
        record,
        schema_name="appraisal",
    )
    return record["id"]


@workspace_scoped
def record_extraction(
    run_id: str,
    *,
    candidate_id: str,
    source_id: str,
    reviewer_id: str,
    field: str,
    status: str,
    rationale: str,
    value: str | None = None,
    segment_id: str | None = None,
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Record one independent protocol-defined extraction field."""
    _, protocol = _frozen_for_run(run_id)
    candidate = _record(workspace_path(RESEARCH_CANDIDATES_DIR), candidate_id)
    if candidate.get("run_id") != run_id or candidate.get("status") != "unique":
        raise ResearchMethodError("extraction candidate does not belong to this run")
    if field not in protocol["extraction_plan"]["fields"]:
        raise ResearchMethodError("extraction field is not in the frozen protocol")
    reviewer = next(
        (r for r in protocol["screening_plan"]["reviewers"] if r["id"] == reviewer_id), None
    )
    if reviewer is None or reviewer["kind"] != "human":
        raise ResearchMethodError(
            "independent extraction requires a protocol-listed human reviewer"
        )
    _require_id(source_id, "src")
    _require_acquired_source(source_id)
    full_text = [
        item
        for item in _records(workspace_path(RESEARCH_SCREENINGS_DIR), "scr_", run_id)
        if item.get("candidate_id") == candidate_id and item.get("stage") == "full_text"
    ]
    if _final_decision(full_text) != "include" or source_id not in {
        item.get("source_id") for item in full_text
    }:
        raise ResearchMethodError("extraction requires the included full-text source")
    if status not in {"reported", "not_reported", "unclear"}:
        raise ResearchMethodError(f"invalid extraction status {status!r}")
    if status == "reported" and (not value or not segment_id):
        raise ResearchMethodError(
            "reported extraction values require text and a supporting segment"
        )
    if segment_id:
        _require_id(segment_id, "seg")
        segment = assert_record_exists(
            segment_id,
            prefix="seg",
            default_dir=workspace_path(EVIDENCE_SEGMENTS_DIR),
            directory_name="segments",
        )
        if segment.get("source_id") != source_id:
            raise ResearchMethodError("extraction segment does not belong to the acquired source")
    for existing in _records(workspace_path(RESEARCH_EXTRACTIONS_DIR), "ext_", run_id):
        if (
            existing.get("candidate_id"),
            existing.get("field"),
            existing.get("reviewer_id"),
            existing.get("record_kind"),
        ) == (candidate_id, field, reviewer_id, "independent"):
            raise ResearchMethodError("reviewer has already extracted this field")
    record: dict[str, Any] = {
        "id": _uuid7("ext"),
        "schema_version": 1,
        "run_id": run_id,
        "protocol_id": protocol["id"],
        "protocol_sha256": protocol["content_sha256"],
        "candidate_id": candidate_id,
        "source_id": source_id,
        "reviewer_id": reviewer_id,
        "field": field,
        "status": status,
        "rationale": rationale,
        "record_kind": "independent",
        "recorded_at": _now(),
    }
    if value is not None:
        record["value"] = value
    if segment_id:
        record["segment_id"] = segment_id
    write_atomic(
        workspace_path(RESEARCH_EXTRACTIONS_DIR) / f"{record['id']}.json",
        record,
        schema_name="extraction",
    )
    return record["id"]


@workspace_scoped
def adjudicate_extraction(
    run_id: str,
    *,
    candidate_id: str,
    source_id: str,
    field: str,
    adjudicator_id: str,
    status: str,
    rationale: str,
    value: str | None = None,
    segment_id: str | None = None,
    workspace: Workspace | Path | str | None = None,
) -> str:
    """Resolve discrepant independent extraction while retaining both inputs."""
    _, protocol = _frozen_for_run(run_id)
    if adjudicator_id != protocol["screening_plan"]["adjudicator"]["id"]:
        raise ResearchMethodError("adjudicator does not match the frozen protocol")
    candidate = _record(workspace_path(RESEARCH_CANDIDATES_DIR), candidate_id)
    if candidate.get("run_id") != run_id or candidate.get("status") != "unique":
        raise ResearchMethodError("extraction adjudication candidate does not belong to this run")
    if field not in protocol["extraction_plan"]["fields"]:
        raise ResearchMethodError("extraction field is not in the frozen protocol")
    _require_id(source_id, "src")
    _require_acquired_source(source_id)
    existing = [
        item
        for item in _records(workspace_path(RESEARCH_EXTRACTIONS_DIR), "ext_", run_id)
        if item.get("candidate_id") == candidate_id and item.get("field") == field
    ]
    if any(item["record_kind"] == "adjudication" for item in existing):
        raise ResearchMethodError("this extraction field already has an adjudication")
    records = [item for item in existing if item.get("record_kind") == "independent"]
    if len(records) < 2 or len({item["reviewer_id"] for item in records}) < 2:
        raise ResearchMethodError("extraction adjudication requires independent reviewer records")
    reviewer_groups = {
        person["independence_group"]
        for item in records
        if (
            person := next(
                (
                    r
                    for r in protocol["screening_plan"]["reviewers"]
                    if r["id"] == item["reviewer_id"]
                ),
                None,
            )
        )
    }
    if len(reviewer_groups) < 2:
        raise ResearchMethodError("extraction reviewers must be independently assigned")
    signatures = {(item["status"], item.get("value")) for item in records}
    if len(signatures) == 1:
        raise ResearchMethodError("extraction adjudication requires a disagreement")
    if status not in {"reported", "not_reported", "unclear"}:
        raise ResearchMethodError(f"invalid extraction status {status!r}")
    if status == "reported" and (not value or not segment_id):
        raise ResearchMethodError("reported adjudication requires value and supporting segment")
    segment = None
    if segment_id:
        _require_id(segment_id, "seg")
        segment = assert_record_exists(
            segment_id,
            prefix="seg",
            default_dir=workspace_path(EVIDENCE_SEGMENTS_DIR),
            directory_name="segments",
        )
        if segment.get("source_id") != source_id:
            raise ResearchMethodError("adjudication segment does not belong to the source")
    full_text = [
        item
        for item in _records(workspace_path(RESEARCH_SCREENINGS_DIR), "scr_", run_id)
        if item.get("candidate_id") == candidate_id and item.get("stage") == "full_text"
    ]
    if _final_decision(full_text) != "include" or source_id not in {
        item.get("source_id") for item in full_text
    }:
        raise ResearchMethodError("extraction adjudication requires the included full-text source")
    record: dict[str, Any] = {
        "id": _uuid7("ext"),
        "schema_version": 1,
        "run_id": run_id,
        "protocol_id": protocol["id"],
        "protocol_sha256": protocol["content_sha256"],
        "candidate_id": candidate_id,
        "source_id": source_id,
        "reviewer_id": adjudicator_id,
        "field": field,
        "status": status,
        "rationale": rationale,
        "record_kind": "adjudication",
        "resolves_extraction_ids": sorted(item["id"] for item in records),
        "recorded_at": _now(),
    }
    if value is not None:
        record["value"] = value
    if segment_id:
        record["segment_id"] = segment_id
    write_atomic(
        workspace_path(RESEARCH_EXTRACTIONS_DIR) / f"{record['id']}.json",
        record,
        schema_name="extraction",
    )
    return record["id"]


@workspace_scoped
def screening_flow(
    run_id: str, *, workspace: Workspace | Path | str | None = None
) -> dict[str, int]:
    """Derive PRISMA-style record flow counts from candidate/decision records."""
    _, protocol = _frozen_for_run(run_id, require_active=False)
    candidates = _records(workspace_path(RESEARCH_CANDIDATES_DIR), "can_", run_id)
    decisions = _records(workspace_path(RESEARCH_SCREENINGS_DIR), "scr_", run_id)
    duplicates = [candidate for candidate in candidates if candidate["status"] == "duplicate"]
    unique = [candidate for candidate in candidates if candidate["status"] == "unique"]
    by_key = {(decision["candidate_id"], decision["stage"]): [] for decision in decisions}
    for decision in decisions:
        by_key[(decision["candidate_id"], decision["stage"])].append(decision)
    final: dict[tuple[str, str], str] = {}
    unresolved = 0
    for key, items in by_key.items():
        independent = [item for item in items if item["decision_kind"] == "independent"]
        adjudications = [item for item in items if item["decision_kind"] == "adjudication"]
        reviewer_groups = {
            reviewer["independence_group"]
            for decision in independent
            if (
                reviewer := next(
                    (
                        person
                        for person in protocol["screening_plan"]["reviewers"]
                        if person["id"] == decision["reviewer_id"]
                    ),
                    None,
                )
            )
        }
        if (
            len(independent) < 2
            or len({item["reviewer_id"] for item in independent}) < 2
            or len(reviewer_groups) < 2
        ):
            unresolved += 1
        elif len({item["outcome"] for item in independent}) == 1:
            final[key] = independent[0]["outcome"]
        elif adjudications:
            final[key] = adjudications[-1]["outcome"]
        else:
            unresolved += 1
    title_included = sum(final.get((c["id"], "title_abstract")) == "include" for c in unique)
    title_excluded = sum(final.get((c["id"], "title_abstract")) == "exclude" for c in unique)
    full_text_assessed = sum((c["id"], "full_text") in final for c in unique)
    full_text_excluded = sum(final.get((c["id"], "full_text")) == "exclude" for c in unique)
    included = sum(final.get((c["id"], "full_text")) == "include" for c in unique)
    searches = _records(workspace_path(RESEARCH_SEARCHES_DIR), "sea_", run_id)
    extractions = _records(workspace_path(RESEARCH_EXTRACTIONS_DIR), "ext_", run_id)
    included_ids = {c["id"] for c in unique if final.get((c["id"], "full_text")) == "include"}
    extraction_total = len(included_ids) * len(protocol["extraction_plan"]["fields"])
    extraction_resolved = sum(
        _final_extraction(
            [
                item
                for item in extractions
                if item["candidate_id"] == candidate_id and item["field"] == field
            ],
            protocol,
        )
        is not None
        for candidate_id in included_ids
        for field in protocol["extraction_plan"]["fields"]
    )
    return {
        "records_identified": sum(search["result_count"] for search in searches),
        "records_represented": len(candidates),
        "duplicates_removed": len(duplicates),
        "records_screened": len(unique),
        "records_excluded_title_abstract": title_excluded,
        "reports_sought": title_included,
        "reports_assessed_full_text": full_text_assessed,
        "reports_excluded_full_text": full_text_excluded,
        "studies_included": included,
        "unresolved_decisions": unresolved,
        "extraction_fields_required": extraction_total,
        "extraction_fields_resolved": extraction_resolved,
        "required_queries": len(protocol["search_plan"]["queries"]),
        "executed_queries": len({search["query_id"] for search in searches}),
    }


@workspace_scoped
def validate_run_for_completion(
    run_id: str, *, workspace: Workspace | Path | str | None = None
) -> list[str]:
    """Return all systematic-review completion blockers in deterministic order."""
    run, protocol = _frozen_for_run(run_id, require_active=False)
    issues: list[str] = []
    flow = screening_flow(run_id)
    searches = _records(workspace_path(RESEARCH_SEARCHES_DIR), "sea_", run_id)
    candidates = _records(workspace_path(RESEARCH_CANDIDATES_DIR), "can_", run_id)
    screenings = _records(workspace_path(RESEARCH_SCREENINGS_DIR), "scr_", run_id)
    appraisals = _records(workspace_path(RESEARCH_APPRAISALS_DIR), "app_", run_id)
    extractions = _records(workspace_path(RESEARCH_EXTRACTIONS_DIR), "ext_", run_id)
    method_records = searches + candidates + screenings + appraisals + extractions
    for record in method_records:
        if (
            record.get("protocol_id") != protocol["id"]
            or record.get("protocol_sha256") != protocol["content_sha256"]
        ):
            issues.append(f"record {record['id']} is not bound to the frozen protocol")
    planned_queries = {item["id"]: item for item in protocol["search_plan"]["queries"]}
    expected_queries = {item["id"] for item in protocol["search_plan"]["queries"]}
    executed_queries = {item["query_id"] for item in searches}
    for search in searches:
        planned = planned_queries.get(search["query_id"])
        expected_parameters = {
            key: planned[key]
            for key in ("date_from", "date_to", "language", "limits")
            if planned and key in planned
        }
        if (
            planned is None
            or any(search.get(key) != planned.get(key) for key in ("database", "platform", "query"))
            or search.get("parameters", {}) != expected_parameters
        ):
            issues.append(f"search {search['id']} does not match the frozen search plan")
        if search["result_count"] > 0 and not (
            search.get("export_location") and search.get("export_sha256")
        ):
            issues.append(f"search {search['id']} has no preserved export reference and hash")
        elif search.get("export_location") and search.get("export_sha256"):
            try:
                _verify_export(search["export_location"], search["export_sha256"])
            except ResearchMethodError as exc:
                issues.append(str(exc))
    if expected_queries - executed_queries:
        issues.append(
            f"unexecuted protocol queries: {', '.join(sorted(expected_queries - executed_queries))}"
        )
    search_ids = {search["id"] for search in searches}
    candidate_ids = {candidate["id"] for candidate in candidates}
    candidate_by_id = {candidate["id"]: candidate for candidate in candidates}
    seen_unique: dict[str, str] = {}
    for candidate in candidates:
        if any(search_id not in search_ids for search_id in candidate["search_ids"]):
            issues.append(f"candidate {candidate['id']} references a missing or foreign search")
        if candidate["status"] == "unique":
            if candidate["dedupe_key"] in seen_unique:
                issues.append(
                    f"duplicate key {candidate['dedupe_key']} has more than one canonical candidate"
                )
            seen_unique[candidate["dedupe_key"]] = candidate["id"]
        else:
            canonical = candidate_by_id.get(candidate.get("duplicate_of", ""))
            if (
                not canonical
                or canonical["status"] != "unique"
                or canonical["dedupe_key"] != candidate["dedupe_key"]
            ):
                issues.append(
                    f"duplicate candidate {candidate['id']} has an invalid canonical reference"
                )
    for record in screenings + appraisals + extractions:
        if record.get("candidate_id") not in candidate_ids:
            issues.append(f"record {record['id']} references a missing candidate")
        if record.get("source_id"):
            try:
                _require_id(record["source_id"], "src")
                assert_record_exists(
                    record["source_id"],
                    prefix="src",
                    default_dir=workspace_path(EVIDENCE_SOURCES_DIR),
                    directory_name="sources",
                )
            except ValueError as exc:
                issues.append(str(exc))
    reviewer_ids = {reviewer["id"] for reviewer in protocol["screening_plan"]["reviewers"]}
    for decision in screenings:
        expected_reviewer = (
            protocol["screening_plan"]["adjudicator"]["id"]
            if decision["decision_kind"] == "adjudication"
            else next(
                (
                    r["id"]
                    for r in protocol["screening_plan"]["reviewers"]
                    if r["kind"] == "human" and r["id"] == decision["reviewer_id"]
                ),
                None,
            )
        )
        if (
            decision["reviewer_id"]
            not in reviewer_ids | {protocol["screening_plan"]["adjudicator"]["id"]}
            or expected_reviewer is None
            or decision["reviewer_id"] != expected_reviewer
        ):
            issues.append(
                f"screening decision {decision['id']} has a reviewer outside the protocol"
            )
    for appraisal in appraisals:
        if (
            appraisal["instrument"] != protocol["appraisal_plan"]["instrument"]
            or appraisal["instrument_version"] != protocol["appraisal_plan"]["instrument_version"]
        ):
            issues.append(f"appraisal {appraisal['id']} differs from the protocol instrument")
        reviewer = next(
            (
                r
                for r in protocol["screening_plan"]["reviewers"]
                if r["id"] == appraisal["reviewer_id"]
            ),
            None,
        )
        if reviewer is None or reviewer["kind"] != "human":
            issues.append(
                f"appraisal {appraisal['id']} has a reviewer outside the human review team"
            )
    for extraction in extractions:
        expected_reviewer = (
            protocol["screening_plan"]["adjudicator"]["id"]
            if extraction["record_kind"] == "adjudication"
            else extraction["reviewer_id"]
        )
        reviewer = next(
            (r for r in protocol["screening_plan"]["reviewers"] if r["id"] == expected_reviewer),
            None,
        )
        if extraction["record_kind"] == "adjudication":
            reviewer_is_valid = (
                extraction["reviewer_id"] == protocol["screening_plan"]["adjudicator"]["id"]
            )
        else:
            reviewer_is_valid = reviewer is not None and reviewer["kind"] == "human"
        if not reviewer_is_valid:
            issues.append(f"extraction {extraction['id']} has a reviewer outside the protocol")
    for extraction in extractions:
        if extraction["field"] not in protocol["extraction_plan"]["fields"]:
            issues.append(f"extraction {extraction['id']} uses a field outside the frozen protocol")
        if extraction.get("segment_id"):
            try:
                _require_id(extraction["segment_id"], "seg")
                segment = assert_record_exists(
                    extraction["segment_id"],
                    prefix="seg",
                    default_dir=workspace_path(EVIDENCE_SEGMENTS_DIR),
                    directory_name="segments",
                )
                if segment.get("source_id") != extraction["source_id"]:
                    issues.append(
                        f"extraction {extraction['id']} cites a segment from another source"
                    )
            except ValueError as exc:
                issues.append(str(exc))
    candidate_counts: dict[str, int] = {}
    for candidate in candidates:
        for search_id in candidate["search_ids"]:
            candidate_counts[search_id] = candidate_counts.get(search_id, 0) + 1
    for search in searches:
        if candidate_counts.get(search["id"], 0) != search["result_count"]:
            issues.append(f"search {search['id']} results are not fully represented as candidates")
    flow_decisions: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for decision in screenings:
        flow_decisions.setdefault((decision["candidate_id"], decision["stage"]), []).append(
            decision
        )
    for candidate in candidates:
        if candidate["status"] == "duplicate":
            continue
        title_key = (candidate["id"], "title_abstract")
        title_items = flow_decisions.get(title_key, [])
        final_title = _final_decision(title_items)
        if final_title is None:
            issues.append(
                f"candidate {candidate['id']} lacks dual title/abstract screening or adjudication"
            )
            continue
        if final_title != "include":
            continue
        full_key = (candidate["id"], "full_text")
        full_items = flow_decisions.get(full_key, [])
        final_full = _final_decision(full_items)
        if final_full is None:
            issues.append(
                f"candidate {candidate['id']} lacks dual full-text screening or adjudication"
            )
        elif final_full == "include":
            final_source = next(
                (d.get("source_id") for d in reversed(full_items) if d.get("source_id")), None
            )
            if not final_source:
                issues.append(f"included candidate {candidate['id']} has no acquired source record")
            elif protocol["appraisal_plan"]["required"] and not any(
                a["candidate_id"] == candidate["id"] and a["source_id"] == final_source
                for a in appraisals
            ):
                issues.append(f"included candidate {candidate['id']} has no required appraisal")
            for field in protocol["extraction_plan"]["fields"]:
                field_records = [
                    item
                    for item in extractions
                    if item["candidate_id"] == candidate["id"] and item["field"] == field
                ]
                if _final_extraction(field_records, protocol) is None:
                    issues.append(
                        f"included candidate {candidate['id']} lacks resolved duplicate extraction for {field!r}"
                    )
                elif any(item["source_id"] != final_source for item in field_records):
                    issues.append(
                        f"extraction for {candidate['id']} field {field!r} references another source"
                    )
    if flow["unresolved_decisions"]:
        issues.append(f"{flow['unresolved_decisions']} screening decisions remain unresolved")
    report_path = workspace_path(RESEARCH_REPORTS_DIR) / f"{run_id}.json"
    if not report_path.is_file():
        issues.append("review audit report has not been generated")
    else:
        try:
            report = _read(report_path)
            digest = report.get("content_sha256")
            if digest != _report_hash(report):
                issues.append("review audit report content hash is invalid")
            elif report.get("protocol_sha256") != protocol["content_sha256"]:
                issues.append("review audit report uses a different protocol")
            elif (
                report.get("flow") != flow
                or report.get("record_ids") != _record_inventory(run_id)
                or report.get("record_hashes") != _record_hashes(run_id)
            ):
                issues.append("review audit report is stale; regenerate it from current records")
        except ResearchMethodError as exc:
            issues.append(str(exc))
    return sorted(set(issues))


def _record_inventory(run_id: str) -> dict[str, list[str]]:
    inventory: dict[str, list[str]] = {}
    for name, directory, prefix in (
        ("searches", workspace_path(RESEARCH_SEARCHES_DIR), "sea_"),
        ("candidates", workspace_path(RESEARCH_CANDIDATES_DIR), "can_"),
        ("screenings", workspace_path(RESEARCH_SCREENINGS_DIR), "scr_"),
        ("appraisals", workspace_path(RESEARCH_APPRAISALS_DIR), "app_"),
        ("extractions", workspace_path(RESEARCH_EXTRACTIONS_DIR), "ext_"),
    ):
        inventory[name] = sorted(record["id"] for record in _records(directory, prefix, run_id))
    sources: set[str] = set()
    for record in _records(workspace_path(RESEARCH_SCREENINGS_DIR), "scr_", run_id):
        if record.get("source_id"):
            sources.add(record["source_id"])
    for record in _records(workspace_path(RESEARCH_APPRAISALS_DIR), "app_", run_id):
        sources.add(record["source_id"])
    inventory["sources"] = sorted(sources)
    claim_records: list[dict[str, Any]] = []
    for path in sorted(workspace_path(EVIDENCE_CLAIMS_DIR).glob("clm_*.json")):
        claim = _read(path)
        try:
            validate("claim", claim)
        except SchemaError as exc:
            raise ResearchMethodError(f"invalid claim record in {path}: {exc}") from exc
        if set(claim.get("source_ids", [])) & sources:
            claim_records.append(claim)
    claim_ids = {claim["id"] for claim in claim_records}
    conflict_ids: list[str] = []
    for path in sorted(workspace_path(EVIDENCE_CONFLICTS_DIR).glob("cfl_*.json")):
        conflict = _read(path)
        try:
            validate("conflict", conflict)
        except SchemaError as exc:
            raise ResearchMethodError(f"invalid conflict record in {path}: {exc}") from exc
        if set(conflict.get("claim_ids", [])) & claim_ids:
            conflict_ids.append(conflict["id"])
    inventory["claims"] = sorted(claim_ids)
    inventory["conflicts"] = sorted(conflict_ids)
    return inventory


def _record_hashes(run_id: str) -> dict[str, str]:
    inventory = _record_inventory(run_id)
    directories = {
        "searches": workspace_path(RESEARCH_SEARCHES_DIR),
        "candidates": workspace_path(RESEARCH_CANDIDATES_DIR),
        "screenings": workspace_path(RESEARCH_SCREENINGS_DIR),
        "extractions": workspace_path(RESEARCH_EXTRACTIONS_DIR),
        "appraisals": workspace_path(RESEARCH_APPRAISALS_DIR),
        "sources": workspace_path(EVIDENCE_SOURCES_DIR),
        "claims": workspace_path(EVIDENCE_CLAIMS_DIR),
        "conflicts": workspace_path(EVIDENCE_CONFLICTS_DIR),
    }
    hashes: dict[str, str] = {}
    for group, ids in inventory.items():
        for record_id in ids:
            path = directories[group] / f"{record_id}.json"
            record = _read(path)
            if record.get("id") != record_id:
                raise ResearchMethodError(f"record identity mismatch in {path}")
            payload = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            hashes[record_id] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return dict(sorted(hashes.items()))


def _report_hash(report: dict[str, Any]) -> str:
    content = {key: value for key, value in report.items() if key != "content_sha256"}
    payload = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@workspace_scoped
def generate_review_report(
    run_id: str,
    *,
    limitations: list[str] | None = None,
    workspace: Workspace | Path | str | None = None,
) -> Path:
    """Write a reproducible audit bundle after screening/appraisal checks pass."""
    run, protocol = _frozen_for_run(run_id, require_active=True)
    issues = validate_run_for_completion(run_id)
    issues = [issue for issue in issues if issue != "review audit report has not been generated"]
    if issues:
        raise ResearchMethodError("review evidence is incomplete: " + "; ".join(issues))
    report: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "protocol_id": protocol["id"],
        "protocol_sha256": protocol["content_sha256"],
        "generated_at": _now(),
        "flow": screening_flow(run_id),
        "record_ids": _record_inventory(run_id),
        "record_hashes": _record_hashes(run_id),
        "limitations": list(limitations or []),
    }
    report["content_sha256"] = _report_hash(report)
    report_path = workspace_path(RESEARCH_REPORTS_DIR) / f"{run_id}.json"
    write_atomic(report_path, report, schema_name="review_report")
    output_ref = f"reports/{run_id}.json"
    outputs = list(run.get("outputs", []))
    if output_ref not in outputs:
        outputs.append(output_ref)
        run["outputs"] = outputs
        write_atomic(workspace_path(RESEARCH_RUNS_DIR) / f"{run_id}.json", run, schema_name="run")
    return report_path


def _final_decision(decisions: list[dict[str, Any]]) -> str | None:
    independent = [item for item in decisions if item["decision_kind"] == "independent"]
    adjudications = [item for item in decisions if item["decision_kind"] == "adjudication"]
    if len(independent) < 2 or len({item["reviewer_id"] for item in independent}) < 2:
        return None
    outcomes = {item["outcome"] for item in independent}
    if len(outcomes) == 1:
        return next(iter(outcomes))
    resolved = set(adjudications[-1].get("resolves_decision_ids", [])) if adjudications else set()
    if len(resolved) == len(independent) and resolved == {item["id"] for item in independent}:
        return adjudications[-1]["outcome"]
    return None


def _final_extraction(
    records: list[dict[str, Any]], protocol: dict[str, Any]
) -> tuple[str, str | None] | None:
    independent = [item for item in records if item["record_kind"] == "independent"]
    adjudications = [item for item in records if item["record_kind"] == "adjudication"]
    if len(independent) < 2 or len({item["reviewer_id"] for item in independent}) < 2:
        return None
    reviewers = protocol["screening_plan"]["reviewers"]
    groups = {
        reviewer["independence_group"]
        for item in independent
        if (reviewer := next((r for r in reviewers if r["id"] == item["reviewer_id"]), None))
    }
    if len(groups) < 2:
        return None
    signatures = {(item["status"], item.get("value")) for item in independent}
    if len(signatures) == 1:
        return next(iter(signatures))
    resolved = set(adjudications[-1].get("resolves_extraction_ids", [])) if adjudications else set()
    if len(resolved) == len(independent) and resolved == {item["id"] for item in independent}:
        return adjudications[-1]["status"], adjudications[-1].get("value")
    return None


__all__ = [
    "ResearchMethodError",
    "adjudicate_extraction",
    "adjudicate_screening",
    "create_protocol",
    "freeze_protocol",
    "generate_review_report",
    "record_appraisal",
    "record_search",
    "record_screening_decision",
    "register_candidate",
    "record_extraction",
    "screening_flow",
    "validate_run_for_completion",
    "verify_run_protocol",
]
