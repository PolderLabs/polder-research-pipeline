"""Atomic write of authoritative JSON records.

Per AUDIT.md §6: writes must be atomic (temp file + validate + rename) and
records must be schema-valid before persistence.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .schemas import SchemaRegistry


class AtomicWriteError(Exception):
    """Raised when an atomic write cannot complete safely."""


def validate_record(
    record: Mapping[str, Any],
    schema_name: str,
    *,
    registry: SchemaRegistry | None = None,
) -> None:
    """Validate a record against a canonical schema; raise SchemaError on failure.

    Writers must call this before any path-touching operation. Validation is the
    normal integrity mechanism — malformed detection by readers is a safety net,
    not an acceptable runtime outcome.
    """
    from .schemas import package_registry

    reg = registry or package_registry()
    reg.validate(schema_name, dict(record))


def write_atomic(
    target: Path,
    record: Mapping[str, Any],
    *,
    schema_name: str | None = None,
    registry: SchemaRegistry | None = None,
) -> None:
    """Write `record` to `target` atomically with optional schema validation.

    Steps:
        1. validate against `schema_name` if provided;
        2. write to a temp file in the same directory;
        3. flush + fsync;
        4. rename over the target (atomic on POSIX).

    Concurrent writes are not arbitrated here — see `acquire_record_lock`
    for optimistic-concurrency helpers used by updaters.
    """
    if schema_name is not None:
        validate_record(record, schema_name, registry=registry)

    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dict(record), indent=2, ensure_ascii=False, sort_keys=False)

    # mkstemp returns an already-open fd; we use it for fsync then unlink.
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, target)
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


__all__ = ["AtomicWriteError", "validate_record", "write_atomic"]
