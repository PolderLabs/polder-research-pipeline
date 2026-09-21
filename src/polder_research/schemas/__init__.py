"""Schema registry — canonical loader for JSON Schema documents from the
repository-root ``schemas/`` directory.
"""

from __future__ import annotations

import json
from typing import Any

import jsonschema

from ..paths import SCHEMAS_DIR

_SCHEMAS: dict[str, dict[str, Any]] = {}

for _p in SCHEMAS_DIR.glob("*.schema.json"):
    _key = _p.stem.replace(".schema", "")
    _SCHEMAS[_key] = json.loads(_p.read_text(encoding="utf-8"))

SCHEMAS: dict[str, dict[str, Any]] = dict(_SCHEMAS)

__all__ = ["SCHEMAS", "get", "validate", "SchemaError", "schemas"]


def schemas() -> dict[str, dict[str, Any]]:
    """Return a copy of the loaded schema registry."""
    return dict(_SCHEMAS)


def get(schema_name: str) -> dict[str, Any]:
    """Return the schema for ``schema_name`` or raise ``KeyError``."""
    return _SCHEMAS[schema_name]


def validate(schema_name: str, instance: Any) -> None:
    """Validate ``instance`` against ``schema_name``."""
    try:
        schema = get(schema_name)
    except KeyError:
        raise SchemaError(f"unknown schema: {schema_name!r}")

    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError as exc:
        raise SchemaError(
            f"validation failed for {schema_name!r}: {exc.message}"
        ) from exc


class SchemaError(Exception):
    """Raised when a schema cannot be loaded or an instance fails validation."""
