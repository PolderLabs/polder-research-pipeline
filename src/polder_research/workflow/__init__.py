"""Rebuildable workflow state derived from authoritative ``.research`` records.

Builders accept an explicit ``repository_root`` so callers (and tests) can
isolate state; when omitted they fall back to the canonical module-level
constants from :mod:`polder_research.paths`, which keeps monkeypatched
redirects working.  Authoritative records are never mutated.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from ..paths import (
    REPO_ROOT,
    RESEARCH_APPRAISALS_DIR,
    RESEARCH_CANDIDATES_DIR,
    RESEARCH_CLASSIFICATIONS_DIR,
    RESEARCH_EVENTS_DIR,
    RESEARCH_EXTRACTIONS_DIR,
    RESEARCH_HANDOFFS_DIR,
    RESEARCH_PROTOCOLS_DIR,
    RESEARCH_RUNS_DIR,
    RESEARCH_SCREENINGS_DIR,
    RESEARCH_SEARCHES_DIR,
    RESEARCH_STATE,
    RESEARCH_TASKS_DIR,
    VAULT_ROOT,
)

_RECORD_TYPES = {
    "events": ("events", "event"),
    "tasks": ("tasks", "task"),
    "runs": ("runs", "run"),
    "handoffs": ("handoffs", "handoff"),
    "protocols": ("protocols", "protocol"),
    "searches": ("searches", "search"),
    "candidates": ("candidates", "candidate"),
    "screenings": ("screenings", "screening"),
    "appraisals": ("appraisals", "appraisal"),
    "extractions": ("extractions", "extraction"),
    "classifications": ("classifications", "classification"),
}


def _root(repository_root: str | Path | None) -> Path | None:
    """Resolve an explicit repository root; ``None`` means canonical constants."""
    if repository_root is None:
        return None
    return Path(repository_root).resolve()


def _config(root: Path | None) -> dict[str, Any]:
    if root is None:
        path = VAULT_ROOT / "research.config.yaml"
    else:
        candidates = (root / "research.config.yaml", root / "knowledge-base" / "research.config.yaml")
        path = next((candidate for candidate in candidates if candidate.is_file()), candidates[0])
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load canonical config {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"canonical config {path} must contain a mapping")
    return value


def _schema(root: Path | None, name: str) -> dict[str, Any]:
    path = (root or REPO_ROOT) / "schemas" / f"{name}.schema.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load canonical schema {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"canonical schema {path} must contain an object")
    return value


def _collection_dirs(root: Path | None) -> dict[str, Path]:
    if root is None:
        return {
            "events": RESEARCH_EVENTS_DIR,
            "tasks": RESEARCH_TASKS_DIR,
            "runs": RESEARCH_RUNS_DIR,
            "handoffs": RESEARCH_HANDOFFS_DIR,
            "protocols": RESEARCH_PROTOCOLS_DIR,
            "searches": RESEARCH_SEARCHES_DIR,
            "candidates": RESEARCH_CANDIDATES_DIR,
            "screenings": RESEARCH_SCREENINGS_DIR,
            "appraisals": RESEARCH_APPRAISALS_DIR,
            "extractions": RESEARCH_EXTRACTIONS_DIR,
            "classifications": RESEARCH_CLASSIFICATIONS_DIR,
        }
    research = root / ".research"
    return {name: research / name for name in _RECORD_TYPES}


def _error_text(error: jsonschema.ValidationError) -> str:
    location = ".".join(str(part) for part in error.absolute_path)
    return f"{location}: {error.message}" if location else error.message


def _read_records(
    root: Path | None,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, str]]]:
    """Load valid records per collection; collect malformed ones separately."""
    records: dict[str, list[dict[str, Any]]] = {}
    malformed: list[dict[str, str]] = []
    dirs = _collection_dirs(root)

    for collection, (directory, schema_name) in _RECORD_TYPES.items():
        valid: list[dict[str, Any]] = []
        paths = sorted(dirs[collection].glob("*.json"))
        if not paths:
            records[collection] = valid
            continue
        validator = jsonschema.Draft202012Validator(_schema(root, schema_name))
        for path in paths:
            relative = f".research/{directory}/{path.name}"
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                malformed.append({"collection": collection, "path": relative, "error": str(exc)})
                continue
            errors = sorted(validator.iter_errors(record), key=lambda item: list(item.path))
            if errors:
                malformed.append(
                    {
                        "collection": collection,
                        "path": relative,
                        "error": "; ".join(_error_text(error) for error in errors),
                    }
                )
                continue
            valid.append(record)
        records[collection] = valid

    malformed.sort(key=lambda item: (item["path"], item["error"]))
    return records, malformed


def _status_summary(records: list[dict[str, Any]], field: str) -> dict[str, Any]:
    by_status = Counter(str(record[field]) for record in records)
    return {
        "total": len(records),
        "by_status": dict(sorted(by_status.items())),
        "ids": [str(record["id"]) for record in sorted(records, key=lambda item: item["id"])],
    }


_WORK_STATUSES: dict[str, frozenset[str]] = {
    "done": frozenset({"completed"}),
    "pending": frozenset({"pending", "awaiting_handoff"}),
    "blocked": frozenset({"blocked"}),
    "leased": frozenset({"leased"}),
    "running": frozenset({"in_progress"}),
    "failed": frozenset({"failed"}),
    "abandoned": frozenset({"abandoned"}),
}


def build_state(repository_root: str | Path | None = None) -> dict[str, Any]:
    """Derive current state without changing any authoritative record.

    Invalid JSON and schema-invalid records are excluded from aggregates and
    exposed in ``malformed``.  Paths are repository-relative so snapshots are
    portable.
    """
    root = _root(repository_root)
    config = _config(root)
    records, malformed = _read_records(root)

    task_statuses = set(config.get("task", {}).get("valid_status", []))
    run_statuses = set(config.get("run", {}).get("valid_status", []))
    handoff_statuses = set(config.get("handoff", {}).get("valid_status", []))
    if not task_statuses or not run_statuses or not handoff_statuses:
        raise ValueError("canonical config is missing workflow status vocabularies")

    tasks = records["tasks"]
    runs = records["runs"]
    handoffs = records["handoffs"]
    work = {
        name: sorted(str(task["id"]) for task in tasks if str(task["status"]) in statuses)
        for name, statuses in _WORK_STATUSES.items()
    }

    return {
        "schema_version": 1,
        "authoritative_root": ".research",
        "work": {name: {"count": len(ids), "ids": ids} for name, ids in work.items()},
        "runs": {
            **_status_summary(runs, "run_status"),
            "running": sorted(str(run["id"]) for run in runs if run["run_status"] == "active"),
            "done": sorted(str(run["id"]) for run in runs if run["run_status"] == "completed"),
        },
        "tasks": _status_summary(tasks, "status"),
        "handoffs": {
            **_status_summary(handoffs, "status"),
            "pending": sorted(
                str(handoff["id"]) for handoff in handoffs if handoff["status"] == "open"
            ),
        },
        "events": {"total": len(records["events"])},
        "classifications": {"total": len(records["classifications"])},
        "method_records": {
            name: len(records[name])
            for name in ("protocols", "searches", "candidates", "screenings", "appraisals", "extractions")
        },
        "malformed": {"count": len(malformed), "records": malformed},
    }


def save_state(
    state: dict[str, Any] | None = None,
    repository_root: str | Path | None = None,
) -> Path:
    """Persist a derived snapshot and return its path."""
    root = _root(repository_root)
    path = RESEARCH_STATE if root is None else root / ".research" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = state if state is not None else build_state(root)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
