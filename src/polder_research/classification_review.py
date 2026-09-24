"""Append-only human decisions for classification proposals.

Reviewer names are recorded for provenance but are not authenticated by this
local-first store. Review decisions never change original model records.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema

from .atomic import write_atomic
from .paths import REPO_ROOT
from .schemas import SchemaRegistry


def _root(repository_root: str | Path | None) -> Path:
    return Path(repository_root).resolve() if repository_root is not None else REPO_ROOT


def _classification(root: Path, classification_id: str) -> dict[str, Any]:
    if not isinstance(classification_id, str) or not re.fullmatch(
        r"cls_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        classification_id,
    ):
        raise ValueError("classification_id must be a valid classification record ID")
    path = root / ".research" / "classifications" / f"{classification_id}.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("classification record was not found or is malformed") from exc
    if not isinstance(record, dict) or record.get("id") != classification_id:
        raise ValueError("classification record identity does not match its filename")
    schema = json.loads((root / "schemas" / "classification.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(record, schema)
    return record


def _validate_value(field: str, value: Any, record: dict[str, Any]) -> None:
    taxonomy = record.get("taxonomy_snapshot", {})
    if field == "category":
        if value is not None and value not in taxonomy.get("categories", {}):
            raise ValueError("reviewed category must be null or a configured category")
    elif field.startswith("tag_"):
        if field.removeprefix("tag_") not in taxonomy.get("tags", {}) or not isinstance(value, bool):
            raise ValueError("reviewed tag must identify a configured tag and use a boolean value")
    elif field.startswith("dimension_"):
        dimension = field.removeprefix("dimension_")
        values = taxonomy.get("dimensions", {}).get(dimension, {}).get("values", {})
        if value is not None and value not in values:
            raise ValueError("reviewed dimension must be null or a configured dimension value")
    else:
        raise ValueError(f"field is not a reviewable taxonomy decision: {field!r}")


def record_review(
    classification_id: str,
    *,
    reviewer: str,
    resolutions: dict[str, dict[str, Any]],
    repository_root: str | Path | None = None,
) -> dict[str, Any]:
    """Persist a review of one or more field proposals without mutating them."""
    root = _root(repository_root)
    if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer.strip()) > 120:
        raise ValueError("reviewer must be a non-empty name or stable reviewer ID")
    if not isinstance(resolutions, dict) or not resolutions:
        raise ValueError("at least one field resolution is required")
    classification = _classification(root, classification_id)
    if classification.get("disposition") == "failed":
        raise ValueError("failed classifications do not contain reviewable proposals")
    decisions = classification.get("field_decisions", {})
    for field, resolution in resolutions.items():
        if field not in decisions:
            raise ValueError(f"classification has no field decision for {field!r}")
        if not isinstance(resolution, dict) or set(resolution) != {"action", "value"}:
            raise ValueError("each resolution requires exactly action and value")
        action, value = resolution["action"], resolution["value"]
        if action not in {"accept", "reject", "edit"}:
            raise ValueError("resolution action must be accept, reject, or edit")
        _validate_value(field, value, classification)
        if action == "accept" and value != decisions[field].get("value"):
            raise ValueError("accept must preserve the proposed value; use edit for a correction")
        if action == "reject":
            rejected = False if field.startswith("tag_") else None
            if value != rejected:
                raise ValueError("reject must use false for tags or null for choices")
        if action == "edit" and value == decisions[field].get("value"):
            raise ValueError("edit must differ from the proposed value")

    review = {
        "id": f"crv_{uuid.uuid7()}",
        "schema_version": 1,
        "classification_id": classification_id,
        "record_key": classification["record_key"],
        "target_kind": classification["target_kind"],
        "target_id": classification["target_id"],
        "input_sha256": classification["input_sha256"],
        "taxonomy_sha256": classification["taxonomy_sha256"],
        "reviewer": reviewer.strip(),
        "resolutions": resolutions,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    output = root / ".research" / "classification_reviews"
    schema_path = root / "schemas" / "classification-review.schema.json"
    if schema_path.is_file():
        jsonschema.validate(review, json.loads(schema_path.read_text(encoding="utf-8")))
        write_atomic(
            output / f"{review['id']}.json",
            review,
            schema_name="classification-review",
            registry=SchemaRegistry(root),
        )
    else:
        raise ValueError("classification review schema is missing from this installation")
    return review


def review_records(repository_root: str | Path | None = None) -> list[dict[str, Any]]:
    """Load valid immutable human review records in creation order."""
    records, _ = review_records_audit(repository_root)
    return records


def review_records_audit(
    repository_root: str | Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Return valid records and integrity errors for every unreadable entry."""
    root = _root(repository_root)
    directory = root / ".research" / "classification_reviews"
    errors: list[dict[str, str]] = []
    if not directory.exists() or not any(directory.glob("*.json")):
        return [], []
    try:
        schema = json.loads(
            (root / "schemas" / "classification-review.schema.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [], [{"path": "schemas/classification-review.schema.json", "error": str(exc)[:300]}]
    validator = jsonschema.Draft202012Validator(schema)
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("crv_*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append({"path": f".research/classification_reviews/{path.name}", "error": str(exc)[:300]})
            continue
        if isinstance(record, dict) and validator.is_valid(record) and record.get("id") == path.stem:
            records.append(record)
        else:
            errors.append({
                "path": f".research/classification_reviews/{path.name}",
                "error": "record failed schema validation or filename identity check",
            })
    return records, errors


__all__ = ["record_review", "review_records", "review_records_audit"]
