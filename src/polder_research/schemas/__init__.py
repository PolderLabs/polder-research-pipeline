"""Canonical JSON Schema registry.

Schema documents live only in a repository root's ``schemas/`` directory.
``SchemaRegistry`` accepts that root explicitly so callers can validate an
isolated repository without mutating process-wide state.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import jsonschema

from ..paths import REPO_ROOT

# ``parents[1]`` is the polder_research package directory; this module lives in
# its ``schemas/`` subpackage, so the bundled copy sits one level up.
BUNDLED_SCHEMAS_DIR: Path = Path(__file__).resolve().parents[1] / "_bundled" / "schemas"


class SchemaError(Exception):
    """Raised when a schema cannot be loaded or an instance fails validation."""


class SchemaRegistry:
    """Load and validate the canonical schemas for one repository root."""

    def __init__(self, repo_root: Path | str | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
        local = self.repo_root / "schemas"
        # A wheel install carries the canonical schemas but not the checkout
        # around them, so fall back to the bundled copy instead of failing.
        self.schema_dir = local if local.is_dir() else BUNDLED_SCHEMAS_DIR
        self._schemas, self._validators = self._load()

    def _load(self) -> tuple[dict[str, dict[str, Any]], dict[str, jsonschema.Draft202012Validator]]:
        if not self.schema_dir.is_dir():
            raise SchemaError(f"schema directory does not exist: {self.schema_dir}")

        loaded: dict[str, dict[str, Any]] = {}
        validators: dict[str, jsonschema.Draft202012Validator] = {}
        ids: set[str] = set()
        for path in sorted(self.schema_dir.glob("*.schema.json")):
            name = path.name.removesuffix(".schema.json")
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SchemaError(f"cannot load schema {path}: {exc}") from exc
            if not isinstance(document, dict):
                raise SchemaError(f"schema {path} must be a JSON object")
            if document.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                raise SchemaError(f"schema {path} must declare Draft 2020-12")
            schema_id = document.get("$id")
            if not isinstance(schema_id, str) or not schema_id:
                raise SchemaError(f"schema {path} must declare a non-empty $id")
            if schema_id in ids:
                raise SchemaError(f"duplicate schema $id {schema_id!r} in {path}")
            ids.add(schema_id)
            try:
                jsonschema.Draft202012Validator.check_schema(document)
            except jsonschema.SchemaError as exc:
                raise SchemaError(f"invalid Draft 2020-12 schema {path}: {exc.message}") from exc
            loaded[name] = document
            validators[name] = jsonschema.Draft202012Validator(
                document, format_checker=jsonschema.FormatChecker()
            )
        return loaded, validators

    def names(self) -> tuple[str, ...]:
        """Return schema names in deterministic filename order."""
        return tuple(self._schemas)

    def schemas(self) -> dict[str, dict[str, Any]]:
        """Return a shallow copy of the registry mapping."""
        return dict(self._schemas)

    def get(self, schema_name: str) -> dict[str, Any]:
        """Return ``schema_name`` or raise ``KeyError``."""
        return self._schemas[schema_name]

    def validator(self, schema_name: str) -> jsonschema.Draft202012Validator:
        """Return the precompiled validator for a canonical schema."""
        try:
            return self._validators[schema_name]
        except KeyError as exc:
            raise SchemaError(f"unknown schema: {schema_name!r}") from exc

    def is_valid(self, schema_name: str, instance: Any) -> bool:
        return self.validator(schema_name).is_valid(instance)

    def validate(self, schema_name: str, instance: Any) -> None:
        """Validate an instance against a canonical named schema."""
        try:
            self.get(schema_name)
        except KeyError as exc:
            raise SchemaError(f"unknown schema: {schema_name!r}") from exc
        errors = list(self.iter_record_errors(schema_name, instance))
        if errors:
            first = errors[0]
            location = first["path"] or "<root>"
            raise SchemaError(
                f"validation failed for {schema_name!r} at {location}: {first['message']}"
            )

    def iter_record_errors(self, schema_name: str, instance: Any) -> tuple[dict[str, str], ...]:
        """Return bounded, deterministically ordered validation errors."""
        try:
            validator = self.validator(schema_name)
        except KeyError as exc:
            raise SchemaError(f"unknown schema: {schema_name!r}") from exc
        errors = sorted(
            validator.iter_errors(instance), key=lambda error: list(error.absolute_path)
        )
        return tuple(
            {
                "path": ".".join(str(part) for part in error.absolute_path),
                "message": error.message[:300],
            }
            for error in errors[:50]
        )

    def validate_filename_identity(self, schema_name: str, filename: str, instance: Any) -> None:
        """Validate the record and require a filename stem matching its id."""
        self.validate(schema_name, instance)
        expected = f"{instance.get('id')}.json" if isinstance(instance, dict) else ""
        if Path(filename).name != expected:
            raise SchemaError(
                f"filename identity mismatch for {schema_name!r}: expected {expected!r}"
            )

    def validate_record(self, schema_name: str, instance: Any) -> None:
        """Compatibility spelling for canonical record validation."""
        self.validate(schema_name, instance)


def registry(repo_root: Path | str | None = None) -> SchemaRegistry:
    """Build a registry from ``repo_root/schemas`` or the package repository."""
    return SchemaRegistry(repo_root)


_PACKAGE_REGISTRY: SchemaRegistry | None = None


def package_registry() -> SchemaRegistry:
    """Return the registry for the canonical schemas shipped with this package.

    Built on first use so that importing the package never depends on a
    checkout being present — a wheel install carries the schemas but not the
    repository that surrounds them.
    """
    global _PACKAGE_REGISTRY
    if _PACKAGE_REGISTRY is None:
        _PACKAGE_REGISTRY = registry()
    return _PACKAGE_REGISTRY


def registry_for_root(repo_root: Path | str | None) -> SchemaRegistry:
    """Return the registry that must validate records for one repository root.

    A root that ships its own ``schemas/`` directory owns validation. Every
    other root — an isolated, temporary, or partial workspace — falls back to
    the package's canonical schemas, so referential and record validation never
    silently disappears just because a root is not a full checkout.
    """
    if repo_root is not None and (Path(repo_root) / "schemas").is_dir():
        return registry(repo_root)
    return package_registry()


def schemas(repo_root: Path | str | None = None) -> dict[str, dict[str, Any]]:
    """Load the canonical schema mapping for ``repo_root``."""
    return registry_for_root(repo_root).schemas()


def get(schema_name: str, repo_root: Path | str | None = None) -> dict[str, Any]:
    """Return a canonical schema by name."""
    return registry_for_root(repo_root).get(schema_name)


def validate(schema_name: str, instance: Any, repo_root: Path | str | None = None) -> None:
    """Validate an instance using the canonical schema registry."""
    registry_for_root(repo_root).validate(schema_name, instance)


class _LazySchemaMapping(Mapping):
    """Read-only view of the package schemas, loaded on first access.

    Exists so ``SCHEMAS`` stays a plain mapping for callers while importing
    this module never requires a repository checkout on disk.
    """

    def __getitem__(self, key: str) -> dict[str, Any]:
        return package_registry().get(key)

    def __iter__(self) -> Iterator[str]:
        return iter(package_registry().names())

    def __len__(self) -> int:
        return len(package_registry().names())

    def keys(self):  # type: ignore[override]
        return package_registry().schemas().keys()


SCHEMAS: Mapping[str, dict[str, Any]] = _LazySchemaMapping()

__all__ = [
    "SCHEMAS",
    "SchemaError",
    "SchemaRegistry",
    "get",
    "package_registry",
    "registry",
    "registry_for_root",
    "schemas",
    "validate",
]
