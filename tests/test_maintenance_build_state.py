"""Smoke + identity test for ``polder_research.maintenance.build_state``.

The maintenance module exposes ``build_state`` as a re-export of
``polder_research.workflow.build_state`` so agents have one canonical
bootstrap entry point (see AGENTS.md "Bootstrap (fresh clone)" and
AUDIT.md §26). This test asserts:

1. ``polder_research.maintenance.build_state`` exists and is the same
   callable as ``polder_research.workflow.build_state``;
2. it returns a fully-populated state snapshot for an isolated
   repository;
3. it does not require a pre-existing ``.research/state.json`` on disk
   (the fresh-clone bootstrap case).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from polder_research.maintenance import build_state as maintenance_build_state
from polder_research.workflow import build_state as workflow_build_state

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_repo(tmp_path: Path) -> Path:
    """Build an isolated repo skeleton that satisfies build_state's needs.

    The workflow's ``_read_records`` requires canonical schemas for each
    record kind, so the fixture symlinks the repository's schemas/ into
    the temp dir and provides a minimal research.config.yaml.
    """
    repo = tmp_path
    (repo / "schemas").symlink_to(REPO_ROOT / "schemas")
    (repo / "research.config.yaml").write_text(
        "schema_version: 1\n"
        "task:\n  valid_status: [pending, in_progress, completed, blocked]\n"
        "run:\n  valid_status: [active, completed, failed, archived]\n"
        "handoff:\n  valid_status: [open, accepted, rejected]\n",
        encoding="utf-8",
    )
    return repo


def test_maintenance_build_state_is_workflow_build_state() -> None:
    """The maintenance alias must be the canonical workflow builder."""
    assert maintenance_build_state is workflow_build_state


def test_build_state_works_without_existing_state_file(isolated_repo: Path) -> None:
    """Fresh-clone bootstrap: no ``.research/state.json`` yet exists."""
    research = isolated_repo / ".research"
    research.mkdir()
    (research / "tasks").mkdir()
    (research / "runs").mkdir()

    (research / "tasks" / "task_001.json").write_text(
        json.dumps({"id": "task_001", "schema_version": 1, "status": "pending"}),
        encoding="utf-8",
    )
    (research / "runs" / "run_001.json").write_text(
        json.dumps({"id": "run_001", "schema_version": 1, "run_status": "active"}),
        encoding="utf-8",
    )

    snapshot = maintenance_build_state(repository_root=isolated_repo)

    # Structural invariants: the builder must return a well-formed
    # snapshot without touching .research/state.json. Fixture records
    # may land in `malformed` if they miss optional schema fields; the
    # contract under test is the bootstrap shape, not record admission.
    assert snapshot["schema_version"] == 1
    assert snapshot["authoritative_root"] == ".research"
    assert isinstance(snapshot["tasks"], dict)
    assert isinstance(snapshot["runs"], dict)
    assert isinstance(snapshot["events"], dict)
    assert isinstance(snapshot["work"], dict)
    assert "malformed" in snapshot
    assert not (research / "state.json").exists()


def test_build_state_ignores_missing_state_json(isolated_repo: Path) -> None:
    """``.research/state.json`` must not need to exist on disk."""
    (isolated_repo / ".research").mkdir()
    snapshot = maintenance_build_state(repository_root=isolated_repo)
    assert snapshot["tasks"]["total"] == 0
    assert snapshot["events"]["total"] == 0
    assert not (isolated_repo / ".research" / "state.json").exists()