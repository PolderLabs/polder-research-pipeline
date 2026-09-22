"""Canonical JSON Schema registry.

Schema documents live only in a repository root's ``schemas/`` directory.
``SchemaRegistry`` accepts that root explicitly so callers can validate an
isolated repository without mutating process-wide state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from ..paths import REPO_ROOT


class SchemaError(Exception):
    """Raised when a schema cannot be loaded or an instance fails validation."""


class SchemaRegistry:
    """Load and validate the canonical schemas for one repository root."""

    def __init__(self, repo_root: Path | str | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
        self.schema_dir = self.repo_root / "schemas"
        self._schemas = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.schema_dir.is_dir():
            raise SchemaError(f"schema directory does not exist: {self.schema_dir}")

        loaded: dict[str, dict[str, Any]] = {}
        for path in sorted(self.schema_dir.glob("*.schema.json")):
            name = path.name.removesuffix(".schema.json")
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SchemaError(f"cannot load schema {path}: {exc}") from exc
            if not isinstance(document, dict):
                raise SchemaError(f"schema {path} must be a JSON object")
            loaded[name] = document
        return loaded

    def names(self) -> tuple[str, ...]:
        """Return schema names in deterministic filename order."""
        return tuple(self._schemas)

    def schemas(self) -> dict[str, dict[str, Any]]:
        """Return a shallow copy of the registry mapping."""
        return dict(self._schemas)

    def get(self, schema_name: str) -> dict[str, Any]:
        """Return ``schema_name`` or raise ``KeyError``."""
        return self._schemas[schema_name]

    def validate(self, schema_name: str, instance: Any) -> None:
        """Validate an instance against a canonical named schema."""
        try:
            schema = self.get(schema_name)
        except KeyError as exc:
            raise SchemaError(f"unknown schema: {schema_name!r}") from exc
        try:
            jsonschema.validate(instance=instance, schema=schema)
        except jsonschema.ValidationError as exc:
            raise SchemaError(f"validation failed for {schema_name!r}: {exc.message}") from exc


def registry(repo_root: Path | str | None = None) -> SchemaRegistry:
    """Build a registry from ``repo_root/schemas`` or the package repository."""
    return SchemaRegistry(repo_root)


_DEFAULT = registry()
SCHEMAS: dict[str, dict[str, Any]] = _DEFAULT.schemas()


def schemas(repo_root: Path | str | None = None) -> dict[str, dict[str, Any]]:
    """Load the canonical schema mapping for ``repo_root``."""
    if repo_root is None:
        return _DEFAULT.schemas()
    return registry(repo_root).schemas()


def get(schema_name: str, repo_root: Path | str | None = None) -> dict[str, Any]:
    """Return a canonical schema by name."""
    if repo_root is None:
        return _DEFAULT.get(schema_name)
    return registry(repo_root).get(schema_name)


def validate(schema_name: str, instance: Any, repo_root: Path | str | None = None) -> None:
    """Validate an instance using the canonical schema registry."""
    if repo_root is None:
        _DEFAULT.validate(schema_name, instance)
    else:
        registry(repo_root).validate(schema_name, instance)


__all__ = [
    "SCHEMAS",
    "SchemaError",
    "SchemaRegistry",
    "get",
    "registry",
    "schemas",
    "validate",
]
