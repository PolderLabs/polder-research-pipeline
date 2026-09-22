"""Smoke + idempotency test for ``scripts/emit_implementation_status.py``.

The emitter writes a fenced ``<!-- status:begin -->`` ... ``<!-- status:end
-->`` block into AUDIT.md with five machine-verified fields
(revision, python, schema_count, test_count, last_audit_revision). Tests
assert:

1. first invocation appends the block (when no sentinels exist yet);
2. second invocation is idempotent (sentinel count stays 1);
3. the block contains exactly the documented field names and backticks;
4. the block correctly reads ``last_audit_revision`` from the AUDIT.md
   front-matter ``Implementation revision inspected:`` line.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
REPO_ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "emit_implementation_status", SCRIPTS_DIR / "emit_implementation_status.py"
)
assert _spec and _spec.loader
emit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(emit)


REQUIRED_FIELDS: tuple[str, ...] = (
    "revision:",
    "python:",
    "schema_count:",
    "test_count:",
    "last_audit_revision:",
)


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Build a minimal repo skeleton for the emitter."""
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas" / "a.schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "schemas" / "b.schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_dummy.py").write_text(
        "def test_x():\n    assert True\n", encoding="utf-8"
    )
    audit = tmp_path / "AUDIT.md"
    audit.write_text(
        "Audit date: 2026-09-22\n"
        "Implementation revision inspected: abc1234567def\n",
        encoding="utf-8",
    )
    return tmp_path


def test_emitter_appends_block_when_no_sentinels(temp_repo: Path) -> None:
    rc = emit.main(["--repository-root", str(temp_repo)])
    assert rc == 0
    text = (temp_repo / "AUDIT.md").read_text()
    assert text.count(emit.BEGIN_SENTINEL) == 1
    assert text.count(emit.END_SENTINEL) == 1
    # Original front-matter survives untouched.
    assert "Implementation revision inspected: abc1234567def" in text
    for field in REQUIRED_FIELDS:
        assert field in text, f"missing field {field!r} in status block"


def test_emitter_is_idempotent(temp_repo: Path) -> None:
    emit.main(["--repository-root", str(temp_repo)])
    text_before = (temp_repo / "AUDIT.md").read_text()
    emit.main(["--repository-root", str(temp_repo)])
    text_after = (temp_repo / "AUDIT.md").read_text()
    # Idempotent on the surrounding file: sentinel count is still 1 and
    # the only changes (if any) are timestamp/revision counter updates.
    assert text_after.count(emit.BEGIN_SENTINEL) == 1
    assert text_after.count(emit.END_SENTINEL) == 1
    # Manual prose above the sentinels is byte-identical.
    head_before = text_before.split(emit.BEGIN_SENTINEL)[0]
    head_after = text_after.split(emit.BEGIN_SENTINEL)[0]
    assert head_before == head_after


def test_block_reads_last_audit_revision(temp_repo: Path) -> None:
    block = emit.build_status_block(temp_repo)
    assert "abc1234567def" in block, "block must surface the front-matter audit revision"


def test_block_reports_schema_count(temp_repo: Path) -> None:
    block = emit.build_status_block(temp_repo)
    assert "schema_count: `2`" in block


def test_block_reports_test_count(temp_repo: Path) -> None:
    block = emit.build_status_block(temp_repo)
    # The dummy test file contributes exactly one test.
    assert "test_count: `1`" in block


def test_block_uses_backticked_fields(temp_repo: Path) -> None:
    block = emit.build_status_block(temp_repo)
    for field in REQUIRED_FIELDS:
        assert f"{field} `" in block, f"field {field!r} must be backticked"


def test_emitter_replaces_block_in_place(tmp_path: Path) -> None:
    """When sentinels already exist, write_block must replace, not append."""
    audit = tmp_path / "AUDIT.md"
    audit.write_text(
        "header\n" + emit.BEGIN_SENTINEL + "\nold body\n" + emit.END_SENTINEL + "\nfooter\n",
        encoding="utf-8",
    )
    emit.write_block(audit, emit.BEGIN_SENTINEL + "\nNEW BODY\n" + emit.END_SENTINEL + "\n")
    text = audit.read_text()
    assert text.count(emit.BEGIN_SENTINEL) == 1
    assert text.count(emit.END_SENTINEL) == 1
    assert "old body" not in text
    assert "NEW BODY" in text
    assert text.startswith("header\n")
    assert text.rstrip().endswith("footer")