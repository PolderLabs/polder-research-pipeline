"""Deterministic maintenance rule evaluation — derived from authoritative
``.research`` records and the canonical ``research.config.yaml``.

This module deliberately contains no scheduler, no executor, and no state
mutation.  It only evaluates whether a maintenance pass is due and, if so,
which structural passes the configuration has authorised.  Builders accept an
explicit ``repository_root`` so callers can isolate state; when omitted they
fall back to the canonical module-level path constants.

Thresholds (incremental interval, unresolved duplicate / critical-conflict
limits, and stale-derivation age) are read from the canonical config rather
than hard-coded.  Callers that need them can use :func:`thresholds`.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..classification_ops import replay_job_health
from ..classification_review import review_records_audit
from ..paths import (
    REPO_ROOT,
    RESEARCH_DIR,
    RESEARCH_HEALTH,
    RESEARCH_RUNS_DIR,
    RESEARCH_TASKS_DIR,
)
from ..schemas import registry_for_root
from ..workflow import _config, _read_records, _root, build_state

# Re-exported from the workflow module so callers can address the canonical
# state builder via ``polder_research.maintenance.build_state`` without
# importing a second module. Slice-C's bootstrap test exercises this alias.
build_state = build_state


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)


def _event_time(record: dict[str, Any]) -> datetime | None:
    timestamp = record.get("timestamp")
    if not isinstance(timestamp, str):
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    # ISO-8601 permits timestamps without an offset. Treat these as UTC so
    # event ordering remains comparable with the UTC clock used by maintenance.
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _updated_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _evidence_collection(root: Path | None, kind: str) -> list[dict[str, Any]]:
    registry = registry_for_root(root or REPO_ROOT, allow_package_fallback=True)
    validator = registry.validator(kind)
    research = RESEARCH_DIR if root is None else root / ".research"
    out: list[dict[str, Any]] = []
    for path in sorted((research / f"{kind}s").glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if (
            validator.is_valid(record)
            and isinstance(record, dict)
            and path.name == f"{record.get('id')}.json"
        ):
            out.append(record)
    return out


def _authorized_passes(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return maintenance passes explicitly enabled by the canonical config."""
    maintenance = config.get("maintenance", {})
    if not isinstance(maintenance, dict):
        raise ValueError("canonical config 'maintenance' block must be a mapping")

    flag_to_pass = (
        ("orphan_check_enabled", "orphan-check"),
        ("frontmatter_check_enabled", "frontmatter-check"),
        ("broken_link_check_enabled", "broken-link-check"),
        ("staleness_check_enabled", "staleness-check"),
    )
    passes: list[dict[str, Any]] = []
    for flag, name in flag_to_pass:
        if maintenance.get(flag, False):
            passes.append({"name": name, "enabled_by": flag})
    return passes


def _threshold(section: dict[str, Any], key: str) -> int | None:
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"maintenance threshold '{key}' must be a non-negative int")
    return value


# Canonical keys the maintenance code reads from ``config['maintenance']``.
# Adding a new threshold here is the single place to teach the code about a
# new tunable; nothing else in the codebase should hard-code it.
_MAINTENANCE_THRESHOLD_KEYS: tuple[str, ...] = (
    "incremental_interval_days",
    "max_unresolved_duplicates",
    "max_unresolved_critical_conflicts",
    "stale_after_days",
)


def thresholds(repository_root: str | Path | None = None) -> dict[str, int | None]:
    """Return the maintenance thresholds read from the canonical config.

    The result maps every key in :data:`_MAINTENANCE_THRESHOLD_KEYS` to its
    configured value (``int``) or ``None`` if the operator omitted it.
    Callers MUST NOT hard-code their own defaults — use this helper.
    """
    root = _root(repository_root)
    config = _config(root)
    maintenance = config.get("maintenance", {})
    if not isinstance(maintenance, dict):
        raise ValueError("canonical config 'maintenance' block must be a mapping")
    return {key: _threshold(maintenance, key) for key in _MAINTENANCE_THRESHOLD_KEYS}


def superseded_source_proxy(
    source: dict[str, Any],
    *,
    repository_root: str | Path | None = None,
) -> str | None:
    """Return the canonical successor source ID for a superseded source.

    Sources use the ``lineage`` block (relation verb ``supersedes``) to
    declare successors, per the canonical source schema. This helper walks
    the source's lineage edges and returns the first ``target`` whose
    ``relation`` is ``supersedes`` (the canonical successor verb).  Returns
    ``None`` when no successor edge exists or the successor source record is
    not present in the evidence collection.
    """
    if not isinstance(source, dict):
        raise TypeError("source must be a mapping")
    lineage = source.get("lineage") or []
    if not isinstance(lineage, list):
        return None
    successor_id: str | None = None
    for edge in lineage:
        if not isinstance(edge, dict):
            continue
        if edge.get("relation") != "supersedes":
            continue
        target = edge.get("target")
        if isinstance(target, str) and target.startswith("src_"):
            successor_id = target
            break
    if successor_id is None:
        return None
    root = _root(repository_root)
    for candidate in _evidence_collection(root, "source"):
        if candidate.get("id") == successor_id:
            return successor_id
    return None


def derive_stale_records(
    records: list[dict[str, Any]],
    *,
    threshold_days: int | None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Flag records whose ``updated_at`` exceeds the configured freshness window.

    The maintenance report emits a ``stale_derived`` finding for every record
    whose ``updated_at`` is older than ``threshold_days`` days from ``now``,
    regardless of the record's declared status. The cutoff lives in YAML
    (``maintenance.stale_after_days``); callers pass the value of
    :func:`thresholds` so the policy is config-driven.
    """
    if threshold_days is None:
        return []
    cutoff = _now(now) - timedelta(days=threshold_days)
    findings: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        updated_at = record.get("updated_at")
        if not isinstance(updated_at, str) or not updated_at:
            continue
        parsed = _updated_time(updated_at)
        if parsed is None:
            continue
        if parsed < cutoff:
            findings.append(
                {
                    "id": record.get("id", ""),
                    "updated_at": updated_at,
                    "age_days": (_now(now) - parsed).days,
                }
            )
    return findings


def evaluate_maintenance(
    repository_root: str | Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate maintenance due without mutating any authoritative record.

    Returns a deterministic snapshot describing:

    - ``due``: whether a maintenance pass is recommended now;
    - ``reason``: the first configured trigger that fired;
    - ``passes``: the structural checks enabled by canonical config;
    - ``thresholds``: numeric limits the operator configured;
    - ``inputs``: counts of authoritative records consulted;
    - ``triggers``: every fired trigger, in fixed evaluation order.
    """
    root = _root(repository_root)
    config = _config(root)
    maintenance = config.get("maintenance", {})
    if not isinstance(maintenance, dict):
        raise ValueError("canonical config 'maintenance' block must be a mapping")

    now = _now(now)
    records, malformed_records = _read_records(root)
    sources = _evidence_collection(root, "source")
    claims = _evidence_collection(root, "claim")
    conflicts = _evidence_collection(root, "conflict")
    superseded_sources = sum(1 for source in sources if source.get("source_status") == "superseded")
    superseded_proxy_ids = sorted(
        {
            sid
            for source in sources
            if (sid := superseded_source_proxy(source, repository_root=root)) is not None
        }
    )

    maintenance_thresholds = thresholds(root)

    acquired_sources = [
        source for source in sources if source.get("acquisition_status") == "acquired"
    ]
    fresh_sources = sum(
        1 for source in acquired_sources if source.get("source_status") == "current"
    )
    stale_sources = sum(1 for source in acquired_sources if source.get("source_status") == "stale")

    open_critical_conflicts = sum(
        1
        for conflict in conflicts
        if conflict.get("status") == "open"
        and str(conflict.get("severity", "medium")) == "critical"
    )

    # Stale derivation: records whose updated_at exceeds the configured
    # ``stale_after_days`` window, regardless of their declared status.
    authoritative_records = (
        list(records["events"])
        + list(records["tasks"])
        + list(records["runs"])
        + list(records["handoffs"])
        + sources
        + claims
        + conflicts
    )
    stale_findings = derive_stale_records(
        authoritative_records,
        threshold_days=maintenance_thresholds.get("stale_after_days"),
        now=now,
    )

    inputs = {
        "sources": len(sources),
        "claims": len(claims),
        "open_conflicts": sum(1 for c in conflicts if c.get("status") == "open"),
        "open_critical_conflicts": open_critical_conflicts,
        "superseded_sources": superseded_sources,
        "superseded_proxies": superseded_proxy_ids,
        "malformed_records": len(malformed_records),
        "fresh_sources": fresh_sources,
        "stale_sources": stale_sources,
        "stale_derived": stale_findings,
    }

    triggers: list[dict[str, str]] = []

    last_maintenance_time = max(
        (
            time
            for event in records["events"]
            if event.get("event_type") == "maintenance.completed"
            and (time := _event_time(event)) is not None
        ),
        default=None,
    )
    days_since_maintenance = (
        (now - last_maintenance_time).total_seconds() / 86_400
        if last_maintenance_time is not None
        else float("inf")
    )
    incremental_days = maintenance_thresholds["incremental_interval_days"]
    if incremental_days is not None and days_since_maintenance >= incremental_days:
        triggers.append(
            {
                "kind": "interval",
                "name": "incremental_interval",
                "reason": (
                    "no maintenance.completed event"
                    if last_maintenance_time is None
                    else f"{days_since_maintenance:.1f}d since last maintenance.completed "
                    f"exceeds interval {incremental_days}d"
                ),
            }
        )

    interval_hours = maintenance.get("health_compute_interval_hours")
    if (
        isinstance(interval_hours, int | float)
        and not isinstance(interval_hours, bool)
        and interval_hours > 0
    ):
        last_health = max(
            (
                time
                for event in records["events"]
                if event.get("event_type") == "health.computed"
                and (time := _event_time(event)) is not None
            ),
            default=None,
        )
        hours_since = (
            (now - last_health).total_seconds() / 3600 if last_health is not None else float("inf")
        )
        if hours_since > interval_hours:
            triggers.append(
                {
                    "kind": "interval",
                    "name": "health_check_interval",
                    "reason": (
                        "no health.computed event"
                        if last_health is None
                        else f"{hours_since:.1f}h since last health.computed "
                        f"exceeds interval {interval_hours}h"
                    ),
                }
            )

    if inputs["stale_sources"] > 0:
        triggers.append(
            {
                "kind": "freshness",
                "name": "stale_sources",
                "reason": f"{inputs['stale_sources']} source(s) are not current",
            }
        )

    max_duplicates = maintenance_thresholds["max_unresolved_duplicates"]
    if max_duplicates is not None and inputs["superseded_sources"] > max_duplicates:
        triggers.append(
            {
                "kind": "threshold",
                "name": "unresolved_duplicates",
                "reason": (
                    f"{inputs['superseded_sources']} superseded source(s) exceeds "
                    f"limit {max_duplicates}"
                ),
            }
        )

    max_critical = maintenance_thresholds["max_unresolved_critical_conflicts"]
    if max_critical is not None and inputs["open_critical_conflicts"] > max_critical:
        triggers.append(
            {
                "kind": "threshold",
                "name": "unresolved_critical_conflicts",
                "reason": (
                    f"{inputs['open_critical_conflicts']} open critical conflict(s) "
                    f"exceeds limit {max_critical}"
                ),
            }
        )

    if inputs["malformed_records"] > 0:
        triggers.append(
            {
                "kind": "anomaly",
                "name": "malformed_records",
                "reason": (
                    f"{inputs['malformed_records']} authoritative record(s) failed validation"
                ),
            }
        )

    if stale_findings:
        triggers.append(
            {
                "kind": "freshness",
                "name": "stale_derived",
                "reason": (
                    f"{len(stale_findings)} authoritative record(s) exceed stale_after_days="
                    f"{maintenance_thresholds.get('stale_after_days')}"
                ),
            }
        )

    passes = _authorized_passes(config)
    due = bool(triggers and passes)
    if due:
        reason = triggers[0]["name"]
    elif triggers:
        reason = "triggered but no maintenance pass is enabled"
    else:
        reason = "no configured trigger fired"

    return {
        "schema_version": 1,
        "evaluated_at": now.isoformat(),
        "due": due,
        "reason": reason,
        "passes": passes,
        "thresholds": maintenance_thresholds,
        "inputs": inputs,
        "triggers": triggers,
    }


def build_health(repository_root: str | Path | None = None) -> dict[str, Any]:
    """Derive a health snapshot without mutating authoritative records."""
    root = _root(repository_root)
    config = _config(root)
    valid_tasks = set(config.get("task", {}).get("valid_status", []))
    valid_runs = set(config.get("run", {}).get("valid_status", []))

    _, malformed = _read_records(root)
    malformed_ids = {item["path"] for item in malformed}

    tasks_dir = RESEARCH_TASKS_DIR if root is None else root / ".research" / "tasks"
    runs_dir = RESEARCH_RUNS_DIR if root is None else root / ".research" / "runs"

    task_counts: Counter[str] = Counter()
    run_counts: Counter[str] = Counter()
    failed_tasks: list[str] = []
    failed_runs: list[str] = []
    blocked_tasks: list[str] = []
    replay_jobs = replay_job_health(root)
    _, malformed_reviews = review_records_audit(root)

    def _load(path: Path) -> dict[str, Any] | None:
        rel = f".research/{path.parent.name}/{path.name}"
        if rel in malformed_ids:
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        return record if isinstance(record, dict) else None

    for record_path in sorted(tasks_dir.glob("*.json")):
        record = _load(record_path)
        if record is None:
            continue
        status = str(record.get("status", "unknown"))
        task_counts[status] += 1
        if status == "failed":
            failed_tasks.append(str(record.get("id", record_path.stem)))
        elif status == "blocked":
            blocked_tasks.append(str(record.get("id", record_path.stem)))
    for record_path in sorted(runs_dir.glob("*.json")):
        record = _load(record_path)
        if record is None:
            continue
        status = str(record.get("run_status", "unknown"))
        run_counts[status] += 1
        if status == "failed":
            failed_runs.append(str(record.get("id", record_path.stem)))

    issues: list[str] = []
    if failed_tasks:
        issues.append(f"failed_tasks={len(failed_tasks)}")
    if failed_runs:
        issues.append(f"failed_runs={len(failed_runs)}")
    if blocked_tasks:
        issues.append(f"blocked_tasks={len(blocked_tasks)}")
    if malformed:
        issues.append(f"malformed_records={len(malformed)}")
    failed_classifications = replay_jobs["targets_by_status"].get("failed", 0)
    if failed_classifications:
        issues.append(f"failed_classification_targets={failed_classifications}")
    if replay_jobs["malformed_count"]:
        issues.append(f"malformed_classification_jobs={replay_jobs['malformed_count']}")
    if malformed_reviews:
        issues.append(f"malformed_classification_reviews={len(malformed_reviews)}")
    unknown_tasks = sorted(
        status for status in task_counts if valid_tasks and status not in valid_tasks
    )
    unknown_runs = sorted(
        status for status in run_counts if valid_runs and status not in valid_runs
    )
    if unknown_tasks:
        issues.append(f"unknown_task_statuses={','.join(unknown_tasks)}")
    if unknown_runs:
        issues.append(f"unknown_run_statuses={','.join(unknown_runs)}")

    return {
        "schema_version": 1,
        "overall": "degraded" if issues else "ok",
        "issues": issues,
        "tasks": {
            "by_status": dict(sorted(task_counts.items())),
            "failed_ids": failed_tasks,
            "blocked_ids": blocked_tasks,
        },
        "runs": {
            "by_status": dict(sorted(run_counts.items())),
            "failed_ids": failed_runs,
        },
        "classification_jobs": replay_jobs,
        "classification_reviews": {
            "malformed_count": len(malformed_reviews),
            "malformed_records": malformed_reviews,
        },
        "malformed_records": [{"path": item["path"], "error": item["error"]} for item in malformed],
    }


def save_health(
    health: dict[str, Any] | None = None,
    repository_root: str | Path | None = None,
) -> Path:
    """Persist a derived health snapshot and return its path."""
    root = _root(repository_root)
    path = RESEARCH_HEALTH if root is None else root / ".research" / "health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = health if health is not None else build_health(root)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def save_maintenance(
    snapshot: dict[str, Any] | None = None,
    repository_root: str | Path | None = None,
) -> Path:
    """Persist a derived maintenance snapshot — diagnostic, not authoritative."""
    root = _root(repository_root)
    research = RESEARCH_DIR if root is None else root / ".research"
    path = research / "maintenance" / "decision.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    snap = snapshot if snapshot is not None else evaluate_maintenance(root)
    path.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
