"""Smoke test for ``scripts/generate_derived.py``.

The generator must:

1. produce a byte-identical snapshot on repeated invocations (no wall
   clock, no filesystem mtimes) — that is the property the CI drift
   check relies on;
2. emit ``.research/generated/state.json`` with per-collection counts,
   last-update timestamps, schema version, and totals;
3. emit ``.research/generated/health.json`` with status and totals;
4. handle a fully empty ``.research`` tree without raising;
5. handle a non-empty collection without raising.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR.parent))
sys.path.insert(0, str(SCRIPTS_DIR.parent / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location("generate_derived", SCRIPTS_DIR / "generate_derived.py")
assert _spec and _spec.loader
generate_derived = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generate_derived)


AUTHORITATIVE_COLLECTIONS = generate_derived.AUTHORITATIVE_COLLECTIONS


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """A repo skeleton with no .research/ tree at all."""
    (tmp_path / "README.md").write_text("# repo\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def populated_repo(tmp_path: Path) -> Path:
    """A repo skeleton with a single record in one collection."""
    (tmp_path / ".research" / "tasks").mkdir(parents=True)
    record = {
        "id": "task_001",
        "schema_version": 1,
        "status": "pending",
        "timestamp": "2026-09-22T10:00:00+00:00",
    }
    (tmp_path / ".research" / "tasks" / "task_001.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    return tmp_path


def test_generator_emits_required_artifacts(empty_repo: Path) -> None:
    derived = generate_derived.build_derived(empty_repo)
    assert set(derived) == {"state", "health"}
    state, health = derived["state"], derived["health"]

    assert state["schema_version"] == generate_derived.STATE_SCHEMA_VERSION
    assert state["authoritative_root"] == ".research"
    assert set(state["collections"]) == set(AUTHORITATIVE_COLLECTIONS)
    for name in AUTHORITATIVE_COLLECTIONS:
        entry = state["collections"][name]
        assert set(entry) == {"count", "malformed", "last_updated", "schema_version"}
        assert entry["count"] == 0
        assert entry["malformed"] == 0
        assert entry["last_updated"] is None
        assert entry["schema_version"] is None

    assert health["schema_version"] == generate_derived.HEALTH_SCHEMA_VERSION
    assert health["status"] in {"green", "yellow", "red"}
    # empty repo with no records -> yellow (intentional, fresh-clone state)
    assert health["status"] == "yellow"
    assert health["totals"]["records"] == 0
    assert set(health["per_collection_counts"]) == set(AUTHORITATIVE_COLLECTIONS)


def test_generator_is_deterministic(empty_repo: Path) -> None:
    """Two consecutive calls must yield byte-identical JSON output.

    This is the property the CI ``git diff --exit-code`` check relies on.
    """
    a = generate_derived.build_derived(empty_repo)
    b = generate_derived.build_derived(empty_repo)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_generator_handles_populated_collection(populated_repo: Path) -> None:
    derived = generate_derived.build_derived(populated_repo)
    state, health = derived["state"], derived["health"]
    assert state["collections"]["tasks"]["count"] == 1
    assert state["collections"]["tasks"]["schema_version"] == "1"
    assert state["collections"]["tasks"]["last_updated"] == "2026-09-22T10:00:00+00:00"
    assert state["totals"]["records"] == 1
    assert state["totals"]["collections_with_records"] == 1
    assert health["status"] == "green"


def test_generator_records_malformed_files(tmp_path: Path) -> None:
    """Malformed JSON is counted but does not raise; health flips to red."""
    (tmp_path / ".research" / "events").mkdir(parents=True)
    (tmp_path / ".research" / "events" / "evt_ok.json").write_text(
        json.dumps({"id": "evt_1", "schema_version": 1}), encoding="utf-8"
    )
    (tmp_path / ".research" / "events" / "evt_bad.json").write_text("{not-json", encoding="utf-8")

    derived = generate_derived.build_derived(tmp_path)
    state, health = derived["state"], derived["health"]
    assert state["collections"]["events"]["count"] == 1
    assert state["collections"]["events"]["malformed"] == 1
    assert health["status"] == "red"


def test_main_writes_files_in_place(tmp_path: Path) -> None:
    """``main()`` writes state.json + health.json under the given root."""
    rc = generate_derived.main(
        ["--repository-root", str(tmp_path)]
    )
    assert rc == 0
    state_path = tmp_path / ".research" / "generated" / "state.json"
    health_path = tmp_path / ".research" / "generated" / "health.json"
    assert state_path.is_file()
    assert health_path.is_file()
    state = json.loads(state_path.read_text())
    assert state["schema_version"] == generate_derived.STATE_SCHEMA_VERSION


def test_generator_uses_record_content_not_mtimes(tmp_path: Path) -> None:
    """The generator must not depend on filesystem mtimes — only record
    content. A record whose ``timestamp`` field is older than its mtime
    must surface the timestamp, not the mtime.
    """
    target = tmp_path / ".research" / "tasks"
    target.mkdir(parents=True)
    record = {
        "id": "task_x",
        "schema_version": 1,
        "status": "pending",
        "timestamp": "1999-01-01T00:00:00+00:00",
    }
    path = target / "task_x.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    # Force a mtime in 2099 to prove mtime is ignored.
    import os

    future = 4_102_444_800  # 2099-01-01
    os.utime(path, (future, future))

    derived = generate_derived.build_derived(tmp_path)
    state = derived["state"]
    assert state["collections"]["tasks"]["last_updated"] == "1999-01-01T00:00:00+00:00"