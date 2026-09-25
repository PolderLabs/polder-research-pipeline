"""Deterministic effective-metadata views derived from evidence and decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..atomic import write_atomic
from ..classification_review import active_review_ids, review_records_audit
from ..schemas import SchemaError, registry_for_root

_TARGETS = {
    "source": "sources",
    "segment": "segments",
    "claim": "claims",
    "entity": "entities",
}


def build_effective_projection(repository_root: str | Path) -> dict[str, Any]:
    """Project eligible legacy taxonomy decisions and active human reviews.

    General-purpose workflow PolicyResults remain queue-only. They cannot
    change effective metadata through this projection.
    """
    root = Path(repository_root)
    registry = registry_for_root(root, allow_package_fallback=True)
    classifications: dict[str, dict[str, Any]] = {}
    directory = root / ".research" / "classifications"
    for path in sorted(directory.glob("cls_*.json")) if directory.exists() else []:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            registry.validate_filename_identity("classification", path.name, record)
        except (OSError, UnicodeError, json.JSONDecodeError, SchemaError):
            continue
        classifications[record["id"]] = record
    reviews, _ = review_records_audit(root)
    active = active_review_ids(reviews)
    review_by_classification: dict[str, list[dict[str, Any]]] = {}
    for review in reviews:
        if review["id"] in active:
            review_by_classification.setdefault(review["classification_id"], []).append(review)

    projected: dict[str, Any] = {}
    for kind, directory_name in _TARGETS.items():
        folder = root / ".research" / directory_name
        for path in sorted(folder.glob("*.json")) if folder.exists() else []:
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                registry.validate_filename_identity(kind, path.name, record)
            except (OSError, UnicodeError, json.JSONDecodeError, SchemaError):
                continue
            values: dict[str, Any] = {}
            target_classifications = [
                result
                for result in classifications.values()
                if result.get("target_kind") == kind and result.get("target_id") == record["id"]
            ]
            target_classifications.sort(
                key=lambda result: (result.get("created_at", ""), result["id"])
            )
            linked_ids = set(record.get("classification_ids", []))
            target_classifications = [
                result
                for result in target_classifications
                if result["id"] in linked_ids or result.get("disposition") != "failed"
            ]
            for result in target_classifications:
                classification_id = result["id"]
                if not result or result.get("disposition") == "failed":
                    continue
                for field, decision in result.get("field_decisions", {}).items():
                    if decision.get("status") == "accepted":
                        values[field] = decision.get("value")
                for review in review_by_classification.get(classification_id, []):
                    for field, resolution in review.get("resolutions", {}).items():
                        values[field] = resolution.get("value")
            metadata = {
                "topic": values.get("category", record.get("topic")),
                "tags": sorted(
                    set(record.get("tags", []))
                    | {
                        field.removeprefix("tag_")
                        for field, value in values.items()
                        if field.startswith("tag_") and value is True
                    }
                ),
                "dimensions": {
                    field.removeprefix("dimension_"): value
                    for field, value in values.items()
                    if field.startswith("dimension_") and value is not None
                },
            }
            projected[f"{kind}:{record['id']}"] = metadata
    return {"schema_version": 1, "records": projected}


def rebuild_effective_projection(repository_root: str | Path) -> Path:
    root = Path(repository_root)
    path = root / ".research" / "generated" / "effective-metadata.json"
    write_atomic(path, build_effective_projection(root))
    return path
