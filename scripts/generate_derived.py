#!/usr/bin/env python3
"""Generate derived state under ``.research/generated/``.

Walks every authoritative record collection under
``.research/{events,tasks,runs,handoffs,sources,segments,claims,entities,
gaps,conflicts,edges}`` and emits two derived artifacts:

- ``.research/generated/state.json`` — per-collection counts, last-update
  timestamps (from record content, not filesystem mtime), the dominant
  schema version per collection, and a top-level ``schema_version``.
- ``.research/generated/health.json`` — aggregate health: totals,
  per-collection counts, malformed-record count, and a derived status.

The output is **derived state** and fully deterministic: given the same
record files, the generator always emits byte-identical JSON (sorted keys,
no wall-clock timestamps — ``generated_at`` is the newest record timestamp
seen, or ``null`` for an empty repository). This is what makes the CI
drift check meaningful:

    python3 scripts/generate_derived.py
    git diff --exit-code -- .research/generated/

``.research/generated/{state,health}.json`` are explicitly tracked despite
the broad ``.research/generated/*`` ignore rule, so a committed snapshot
that no longer matches what the repository alone can regenerate fails CI.

Usage:

  python3 scripts/generate_derived.py [--repository-root PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]

# Every authoritative collection the generator must inspect, in a stable
# order so the output is deterministic regardless of glob ordering.
AUTHORITATIVE_COLLECTIONS: tuple[str, ...] = (
    "events",
    "tasks",
    "runs",
    "handoffs",
    "sources",
    "segments",
    "claims",
    "entities",
    "gaps",
    "conflicts",
    "edges",
)

STATE_SCHEMA_VERSION = 1
HEALTH_SCHEMA_VERSION = 1

# Record fields that may carry the record's own last-update timestamp, in
# priority order. Filesystem mtime is deliberately NOT used: CI checkouts
# rewrite mtimes, which would make the artifact machine-dependent.
_TIMESTAMP_FIELDS: tuple[str, ...] = ("timestamp", "updated_at", "created_at")


def _read_record(path: Path) -> dict[str, Any] | None:
    """Return the parsed JSON object record, or ``None`` if unparseable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _record_timestamp(record: dict[str, Any]) -> str | None:
    """Return the record's own timestamp field, if any (ISO string)."""
    for field in _TIMESTAMP_FIELDS:
        value = record.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def _collect(repository_root: Path) -> dict[str, dict[str, Any]]:
    """Aggregate every authoritative collection from record content only."""
    research = repository_root / ".research"
    snapshot: dict[str, dict[str, Any]] = {}
    for name in AUTHORITATIVE_COLLECTIONS:
        directory = research / name
        count = 0
        malformed = 0
        last_updated: str | None = None
        schema_versions: Counter[str] = Counter()
        if directory.is_dir():
            for path in sorted(directory.glob("*.json")):
                record = _read_record(path)
                if record is None:
                    malformed += 1
                    continue
                count += 1
                ts = _record_timestamp(record)
                if ts is not None and (last_updated is None or ts > last_updated):
                    last_updated = ts
                version = record.get("schema_version")
                if isinstance(version, str | int):
                    schema_versions[str(version)] += 1
        snapshot[name] = {
            "count": count,
            "malformed": malformed,
            "last_updated": last_updated,
            "schema_version": schema_versions.most_common(1)[0][0] if schema_versions else None,
        }
    return snapshot


def build_derived(repository_root: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return the derived ``state`` and ``health`` payloads (pure function)."""
    root = repository_root or REPO_ROOT_DEFAULT
    snapshot = _collect(root)

    total_records = sum(item["count"] for item in snapshot.values())
    total_malformed = sum(item["malformed"] for item in snapshot.values())
    newest = max(
        (item["last_updated"] for item in snapshot.values() if item["last_updated"]),
        default=None,
    )
    collections_with_records = sum(1 for item in snapshot.values() if item["count"] > 0)

    state: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSION,
        "authoritative_root": ".research",
        "generated_at": newest,
        "collections": {name: snapshot[name] for name in AUTHORITATIVE_COLLECTIONS},
        "totals": {
            "records": total_records,
            "malformed": total_malformed,
            "collections_with_records": collections_with_records,
        },
    }

    if total_malformed > 0:
        status = "red"
    elif total_records == 0:
        # An empty record store is expected on a fresh clone: authoritative
        # records are local-only (gitignored); the repo ships none.
        status = "yellow"
    else:
        status = "green"

    health: dict[str, Any] = {
        "schema_version": HEALTH_SCHEMA_VERSION,
        "status": status,
        "generated_at": newest,
        "totals": state["totals"],
        "per_collection_counts": {
            name: snapshot[name]["count"] for name in AUTHORITATIVE_COLLECTIONS
        },
    }
    return {"state": state, "health": health}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=REPO_ROOT_DEFAULT,
        help="Repository root containing the .research/ tree (default: script parent).",
    )
    args = parser.parse_args(argv)

    derived = build_derived(args.repository_root)
    generated = args.repository_root / ".research" / "generated"
    _write_json(generated / "state.json", derived["state"])
    _write_json(generated / "health.json", derived["health"])
    print(
        f"wrote {generated / 'state.json'} and {generated / 'health.json'} "
        f"(status={derived['health']['status']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
