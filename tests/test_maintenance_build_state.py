"""Smoke + identity test for ``polder_research.maintenance.build_state``.

The maintenance module exposes ``build_state`` as a re-export of
``polder_research.workflow.build_state`` so agents have one canonical
bootstrap entry point (see AGENTS.md "Bootstrap (fresh clone)" and
AUDIT.md §26). This test asserts:

1. ``polder_research.maintenance.build_state`` exists;
2. it is the same callable as ``polder_research.workflow.build_state``;
3. it returns a fully-populated state snapshot for a repository that
   contains both task records and an event log;
4. it does not require a pre-existing ``.research/state.json`` (the
   bootstrap case — fresh clone has no derived snapshot yet).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from polder_research.maintenance import build_state as maintenance_build_state
from polder_research.workflow import build_state as workflow_build_state


def test_maintenance_build_state_is_workflow_build_state() -> None:
    """The maintenance alias must be the canonical workflow builder."""
    assert maintenance_build_state is workflow_build_state


def test_build_state_works_without_existing_state_file(tmp_path: Path) -> None:
    """Fresh-clone bootstrap: no ``.research/state.json`` yet exists."""
    research = tmp_path / ".research"
    research.mkdir()
    tasks_dir = research / "tasks"
    tasks_dir.mkdir()
    runs_dir = research / "runs"
    runs_dir.mkdir()

    # Provide a minimal valid task and run.
    (tasks_dir / "task_001.json").write_text(
        json.dumps(
            {
                "id": "task_001",
                "schema_version": 1,
                "status": "pending",
                "title": "Test task",
            }
        ),
        encoding="utf-8",
    )
    (runs_dir / "run_001.json").write_text(
        json.dumps(
            {
                "id": "run_001",
                "schema_version": 1,
                "run_status": "active",
                "title": "Test run",
            }
        ),
        encoding="utf-8",
    )
    # A research.config.yaml so build_state() can read status vocabularies.
    (tmp_path / "research.config.yaml").write_text(
        "schema_version: 1\n"
        "task:\n  valid_status: [pending, in_progress, completed, blocked]\n"
        "run:\n  valid_status: [active, completed, failed, archived]\n"
        "handoff:\n  valid_status: [open, accepted, rejected]\n",
        encoding="utf-8",
    )

    snapshot = maintenance_build_state(repository_root=tmp_path)

    assert snapshot["schema_version"] == 1
    assert snapshot["authoritative_root"] == ".research"
    assert "task_001" in snapshot["tasks"]["ids"]
    assert snapshot["tasks"]["by_status"].get("pending") == 1
    assert "run_001" in snapshot["runs"]["running"]
    assert "malformed" in snapshot


def test_build_state_ignores_missing_state_json(tmp_path: Path) -> None:
    """``.research/state.json`` must not need to exist on disk."""
    # Only an empty .research dir; no authoritative records.
    (tmp_path / ".research").mkdir()
    (tmp_path / "research.config.yaml").write_text(
        "schema_version: 1\n"
        "task:\n  valid_status: [pending]\n"
        "run:\n  valid_status: [active]\n"
        "handoff:\n  valid_status: [open]\n",
        encoding="utf-8",
    )
    snapshot = maintenance_build_state(repository_root=tmp_path)
    assert snapshot["tasks"]["total"] == 0
    assert snapshot["events"]["total"] == 0
    # The derived state lives in the returned dict; the on-disk .research/
    # state.json was never read.
    assert not (tmp_path / ".research" / "state.json").exists()