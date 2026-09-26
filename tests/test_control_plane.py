"""Behavioral tests for the P2 control plane: state builder, health builder,
deterministic maintenance rule evaluation.

These tests exercise consumer-visible behavior — what an agent observes when
it inspects the derived snapshots — without mutating authoritative records.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _minimal_config(extra_maintenance: str = "") -> str:
    """A small canonical-shaped config that exposes the maintenance knobs."""
    return (
        "schema_version: 1\n"
        "task:\n"
        "  valid_status:\n"
        "    - pending\n    - leased\n    - in_progress\n    - awaiting_handoff\n"
        "    - completed\n    - failed\n    - blocked\n    - abandoned\n"
        "run:\n"
        "  valid_status:\n"
        "    - draft\n    - active\n    - paused\n    - completed\n    - aborted\n    - failed\n"
        "handoff:\n"
        "  valid_status:\n"
        "    - open\n    - accepted\n    - rejected\n    - expired\n"
        "maintenance:\n"
        "  incremental_interval_days: 365\n"
        "  max_unresolved_duplicates: 999\n"
        "  max_unresolved_critical_conflicts: 999\n"
        "  orphan_check_enabled: false\n"
        "  frontmatter_check_enabled: false\n"
        "  broken_link_check_enabled: false\n"
        "  staleness_check_enabled: false\n"
        "  health_compute_interval_hours: 8760\n"
        f"{extra_maintenance}"
    )


@pytest.fixture(autouse=True)
def _patch_config_path(monkeypatch, tmp_path: Path):
    """Synthesise a minimal repository with required schemas and config."""
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    for name in ("event", "task", "run", "handoff", "source", "claim", "conflict"):
        src = REPO_ROOT / "schemas" / f"{name}.schema.json"
        (schemas / f"{name}.schema.json").write_text(src.read_text(encoding="utf-8"))

    research = tmp_path / ".research"
    for sub in (
        "events",
        "tasks",
        "runs",
        "handoffs",
        "maintenance",
        "locks",
        "generated",
        "sources",
        "claims",
        "entities",
        "segments",
        "gaps",
        "conflicts",
    ):
        (research / sub).mkdir(parents=True, exist_ok=True)

    (tmp_path / "research.config.yaml").write_text(_minimal_config())

    return tmp_path


def _write(research: Path, rel: str, payload) -> Path:
    path = research / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, dict | list):
        path.write_text(json.dumps(payload))
    else:
        path.write_text(payload)
    return path


def _task(task_id: str, status: str, **extras) -> dict:
    record = {
        "id": task_id,
        "schema_version": 1,
        "task_kind": "process",
        "status": status,
        "role": "acquisition",
        "summary": "s",
        "created_at": "2026-09-22T00:00:00Z",
    }
    record.update(extras)
    return record


def _run(run_id: str, run_status: str) -> dict:
    return {
        "id": run_id,
        "schema_version": 1,
        "run_status": run_status,
        "created_at": "2026-09-22T00:00:00Z",
        "brief": {"question": "Q"},
    }


def _event(event_id: str, event_type: str, timestamp: str, **extras) -> dict:
    record = {
        "id": event_id,
        "event_type": event_type,
        "actor": "test",
        "timestamp": timestamp,
        "instruction_version": "0.1.0",
        "config_version": "unavailable",
        "code_revision": "HEAD",
    }
    record.update(extras)
    return record


def _source(source_id: str, status: str) -> dict:
    return {
        "id": source_id,
        "schema_version": 1,
        "source_status": status,
        "acquisition_status": "acquired",
        "source_type": "paper",
        "media_type": "pdf",
        "title": "t",
        "retrieved_at": "2026-09-22T00:00:00Z",
        "content_sha256": "a" * 64,
    }


def _set_config(tmp_path: Path, body: str) -> None:
    (tmp_path / "research.config.yaml").write_text(body)


class TestStateBuilder:
    def test_reports_work_statuses(self, tmp_path):
        research = tmp_path / ".research"
        _write(
            research,
            "tasks/tsk_11111111-1111-7111-8111-111111111111.json",
            _task("tsk_11111111-1111-7111-8111-111111111111", "pending"),
        )
        _write(
            research,
            "tasks/tsk_22222222-2222-7222-8222-222222222222.json",
            _task("tsk_22222222-2222-7222-8222-222222222222", "leased"),
        )
        _write(
            research,
            "tasks/tsk_33333333-3333-7333-8333-333333333333.json",
            _task("tsk_33333333-3333-7333-8333-333333333333", "in_progress"),
        )
        _write(
            research,
            "tasks/tsk_44444444-4444-7444-8444-444444444444.json",
            _task("tsk_44444444-4444-7444-8444-444444444444", "completed"),
        )
        _write(
            research,
            "tasks/tsk_55555555-5555-7555-8555-555555555555.json",
            _task("tsk_55555555-5555-7555-8555-555555555555", "blocked"),
        )

        from polder_research.workflow import build_state

        state = build_state(tmp_path)

        assert state["schema_version"] == 1
        assert state["work"]["done"]["count"] == 1
        assert state["work"]["pending"]["count"] == 1
        assert state["work"]["blocked"]["count"] == 1
        assert state["work"]["leased"]["count"] == 1
        assert state["work"]["running"]["count"] == 1
        assert "tsk_44444444-4444-7444-8444-444444444444" in state["work"]["done"]["ids"]

    def test_reports_running_and_done_runs(self, tmp_path):
        research = tmp_path / ".research"
        _write(
            research,
            "runs/run_11111111-1111-7111-8111-111111111111.json",
            _run("run_11111111-1111-7111-8111-111111111111", "active"),
        )
        _write(
            research,
            "runs/run_22222222-2222-7222-8222-222222222222.json",
            _run("run_22222222-2222-7222-8222-222222222222", "completed"),
        )

        from polder_research.workflow import build_state

        state = build_state(tmp_path)

        assert state["runs"]["running"] == ["run_11111111-1111-7111-8111-111111111111"]
        assert state["runs"]["done"] == ["run_22222222-2222-7222-8222-222222222222"]
        assert state["runs"]["by_status"]["active"] == 1
        assert state["runs"]["by_status"]["completed"] == 1

    def test_reports_open_handoffs(self, tmp_path):
        research = tmp_path / ".research"
        _write(
            research,
            "handoffs/hnd_11111111-1111-7111-8111-111111111111.json",
            {
                "id": "hnd_11111111-1111-7111-8111-111111111111",
                "schema_version": 1,
                "from_role": "curator",
                "to_role": "acquisition",
                "status": "open",
                "summary": "h",
                "created_at": "2026-09-22T00:00:00Z",
            },
        )

        from polder_research.workflow import build_state

        state = build_state(tmp_path)

        assert state["handoffs"]["pending"] == ["hnd_11111111-1111-7111-8111-111111111111"]
        assert state["handoffs"]["by_status"]["open"] == 1

    def test_reports_malformed_records_without_dropping_valid(self, tmp_path):
        research = tmp_path / ".research"
        _write(
            research,
            "tasks/tsk_11111111-1111-7111-8111-111111111111.json",
            _task("tsk_11111111-1111-7111-8111-111111111111", "completed"),
        )
        _write(research, "tasks/broken.json", {"id": "tsk_x", "status": "pending"})
        _write(research, "tasks/garbage.json", "{not json")
        _write(research, "runs/bad_run.json", "not-json")

        from polder_research.workflow import build_state

        state = build_state(tmp_path)

        assert state["work"]["done"]["count"] == 1
        assert state["malformed"]["count"] == 3
        paths = {entry["path"] for entry in state["malformed"]["records"]}
        assert ".research/tasks/broken.json" in paths
        assert ".research/tasks/garbage.json" in paths
        assert ".research/runs/bad_run.json" in paths
        collections = {entry["collection"] for entry in state["malformed"]["records"]}
        assert collections == {"tasks", "runs"}

    def test_save_state_writes_snapshot(self, tmp_path):
        research = tmp_path / ".research"
        _write(
            research,
            "tasks/tsk_11111111-1111-7111-8111-111111111111.json",
            _task("tsk_11111111-1111-7111-8111-111111111111", "completed"),
        )

        from polder_research.workflow import save_state

        path = save_state(repository_root=tmp_path)
        assert path == tmp_path / ".research" / "state.json"
        snapshot = json.loads(path.read_text())
        assert snapshot["work"]["done"]["count"] == 1


class TestHealthBuilder:
    def test_overall_ok_when_no_issues(self, tmp_path):
        from polder_research.maintenance import build_health

        health = build_health(tmp_path)
        assert health["overall"] == "ok"
        assert health["issues"] == []
        assert health["tasks"]["failed_ids"] == []

    def test_reports_failed_and_blocked_tasks(self, tmp_path):
        research = tmp_path / ".research"
        _write(
            research,
            "tasks/tsk_11111111-1111-7111-8111-111111111111.json",
            _task("tsk_11111111-1111-7111-8111-111111111111", "failed"),
        )
        _write(
            research,
            "tasks/tsk_22222222-2222-7222-8222-222222222222.json",
            _task("tsk_22222222-2222-7222-8222-222222222222", "blocked"),
        )

        from polder_research.maintenance import build_health

        health = build_health(tmp_path)
        assert health["overall"] == "degraded"
        assert any(issue.startswith("failed_tasks=") for issue in health["issues"])
        assert any(issue.startswith("blocked_tasks=") for issue in health["issues"])
        assert health["tasks"]["failed_ids"] == ["tsk_11111111-1111-7111-8111-111111111111"]
        assert health["tasks"]["blocked_ids"] == ["tsk_22222222-2222-7222-8222-222222222222"]

    def test_reports_failed_runs(self, tmp_path):
        research = tmp_path / ".research"
        _write(
            research,
            "runs/run_11111111-1111-7111-8111-111111111111.json",
            _run("run_11111111-1111-7111-8111-111111111111", "failed"),
        )

        from polder_research.maintenance import build_health

        health = build_health(tmp_path)
        assert any(issue.startswith("failed_runs=") for issue in health["issues"])
        assert health["runs"]["failed_ids"] == ["run_11111111-1111-7111-8111-111111111111"]

    def test_malformed_records_surface_as_health_issue(self, tmp_path):
        research = tmp_path / ".research"
        _write(research, "runs/bad_run.json", "not-json")

        from polder_research.maintenance import build_health

        health = build_health(tmp_path)
        assert health["overall"] == "degraded"
        assert any(issue.startswith("malformed_records=") for issue in health["issues"])
        assert health["malformed_records"]


class TestMaintenanceEvaluation:
    def test_first_pass_due_with_no_history(self, tmp_path):
        """A repository with no maintenance history is due for its first pass."""
        _set_config(
            tmp_path,
            _minimal_config("  staleness_check_enabled: true\n"),
        )
        from polder_research.maintenance import evaluate_maintenance

        snap = evaluate_maintenance(
            tmp_path,
            now=datetime(2026, 9, 22, 12, tzinfo=UTC),
        )

        names = [trigger["name"] for trigger in snap["triggers"]]
        assert names == ["incremental_interval", "health_check_interval"]
        assert snap["due"] is True
        assert snap["reason"] == "incremental_interval"

    def test_not_due_when_fresh_history_and_no_anomalies(self, tmp_path):
        research = tmp_path / ".research"
        _write(
            research,
            "events/evt_11111111-1111-7111-8111-111111111111.json",
            _event(
                "evt_11111111-1111-7111-8111-111111111111",
                "maintenance.completed",
                "2026-09-22T00:00:00Z",
            ),
        )
        _write(
            research,
            "events/evt_22222222-2222-7222-8222-222222222222.json",
            _event(
                "evt_22222222-2222-7222-8222-222222222222",
                "health.computed",
                "2026-09-22T00:00:00Z",
            ),
        )

        from polder_research.maintenance import evaluate_maintenance

        snap = evaluate_maintenance(
            tmp_path,
            now=datetime(2026, 9, 22, 12, tzinfo=UTC),
        )

        assert snap["triggers"] == []
        assert snap["due"] is False
        assert snap["reason"] == "no configured trigger fired"

    def test_due_when_stale_sources_present(self, tmp_path):
        _set_config(
            tmp_path,
            _minimal_config("  staleness_check_enabled: true\n"),
        )
        research = tmp_path / ".research"
        _write(
            research,
            "sources/src_11111111-1111-7111-8111-111111111111.json",
            _source("src_11111111-1111-7111-8111-111111111111", "stale"),
        )

        from polder_research.maintenance import evaluate_maintenance

        snap = evaluate_maintenance(
            tmp_path,
            now=datetime(2026, 9, 22, 12, tzinfo=UTC),
        )

        assert snap["due"] is True
        names = [trigger["name"] for trigger in snap["triggers"]]
        assert "stale_sources" in names
        assert "staleness-check" in {p["name"] for p in snap["passes"]}

    def test_due_blocked_when_no_pass_enabled(self, tmp_path):
        research = tmp_path / ".research"
        _write(
            research,
            "sources/src_11111111-1111-7111-8111-111111111111.json",
            _source("src_11111111-1111-7111-8111-111111111111", "stale"),
        )

        from polder_research.maintenance import evaluate_maintenance

        snap = evaluate_maintenance(
            tmp_path,
            now=datetime(2026, 9, 22, 12, tzinfo=UTC),
        )

        assert snap["due"] is False
        assert snap["reason"] == "triggered but no maintenance pass is enabled"
        assert snap["passes"] == []

    def test_threshold_triggers_for_duplicates(self, tmp_path):
        _set_config(
            tmp_path,
            _minimal_config("  max_unresolved_duplicates: 5\n"),
        )
        research = tmp_path / ".research"
        for i in range(12):
            sid = f"src_{i:08x}-1111-7111-8111-111111111111"
            _write(research, f"sources/{sid}.json", _source(sid, "superseded"))

        from polder_research.maintenance import evaluate_maintenance

        snap = evaluate_maintenance(
            tmp_path,
            now=datetime(2026, 9, 22, 12, tzinfo=UTC),
        )

        names = [trigger["name"] for trigger in snap["triggers"]]
        assert "unresolved_duplicates" in names

    def test_threshold_triggers_for_open_critical_conflicts(self, tmp_path):
        _set_config(
            tmp_path,
            _minimal_config("  max_unresolved_critical_conflicts: 0\n"),
        )
        research = tmp_path / ".research"
        _write(
            research,
            "conflicts/cfl_11111111-1111-7111-8111-111111111111.json",
            {
                "id": "cfl_11111111-1111-7111-8111-111111111111",
                "schema_version": 1,
                "status": "open",
                "severity": "critical",
                "created_at": "2026-09-22T00:00:00Z",
                "claim_ids": [
                    "clm_11111111-1111-7111-8111-111111111111",
                    "clm_22222222-2222-7222-8222-222222222222",
                ],
            },
        )

        from polder_research.maintenance import evaluate_maintenance

        snap = evaluate_maintenance(
            tmp_path,
            now=datetime(2026, 9, 22, 12, tzinfo=UTC),
        )

        names = [trigger["name"] for trigger in snap["triggers"]]
        assert "unresolved_critical_conflicts" in names

    def test_malformed_records_trigger_anomaly(self, tmp_path):
        research = tmp_path / ".research"
        _write(research, "runs/bad_run.json", "not-json")

        from polder_research.maintenance import evaluate_maintenance

        snap = evaluate_maintenance(
            tmp_path,
            now=datetime(2026, 9, 22, 12, tzinfo=UTC),
        )

        names = [trigger["name"] for trigger in snap["triggers"]]
        assert "malformed_records" in names

    def test_deterministic_for_fixed_clock(self, tmp_path):
        _set_config(
            tmp_path,
            _minimal_config("  staleness_check_enabled: true\n"),
        )
        research = tmp_path / ".research"
        _write(
            research,
            "sources/src_11111111-1111-7111-8111-111111111111.json",
            _source("src_11111111-1111-7111-8111-111111111111", "stale"),
        )
        _write(research, "runs/bad_run.json", "not-json")

        fixed_now = datetime(2026, 9, 22, 12, tzinfo=UTC)

        from polder_research.maintenance import evaluate_maintenance

        first = evaluate_maintenance(tmp_path, now=fixed_now)
        second = evaluate_maintenance(tmp_path, now=fixed_now)
        assert first == second
        assert first["due"] is True
        names = [trigger["name"] for trigger in first["triggers"]]
        assert names == [
            "incremental_interval",
            "health_check_interval",
            "stale_sources",
            "malformed_records",
        ]

    def test_incremental_interval_trigger(self, tmp_path):
        _set_config(
            tmp_path,
            _minimal_config("  incremental_interval_days: 7\n"),
        )
        research = tmp_path / ".research"
        _write(
            research,
            "events/evt_11111111-1111-7111-8111-111111111111.json",
            _event(
                "evt_11111111-1111-7111-8111-111111111111",
                "maintenance.completed",
                "2026-09-01T00:00:00Z",
            ),
        )

        from polder_research.maintenance import evaluate_maintenance

        snap = evaluate_maintenance(
            tmp_path,
            now=datetime(2026, 9, 22, 12, tzinfo=UTC),
        )

        names = [trigger["name"] for trigger in snap["triggers"]]
        assert "incremental_interval" in names

    def test_save_maintenance_returns_path(self, tmp_path):
        from polder_research.maintenance import save_maintenance

        path = save_maintenance(repository_root=tmp_path)
        assert path == tmp_path / ".research" / "maintenance" / "decision.json"
        payload = json.loads(path.read_text())
        assert payload["schema_version"] == 1


class TestRepositoryRootIndependence:
    def test_builders_accept_repository_root(self, tmp_path):
        """Verify builders never reach for module-level REPO_ROOT."""
        from polder_research.maintenance import build_health, evaluate_maintenance
        from polder_research.workflow import build_state

        state = build_state(tmp_path)
        health = build_health(tmp_path)
        snap = evaluate_maintenance(tmp_path)

        expected_work = {
            name: {"count": 0, "ids": []}
            for name in ("done", "pending", "blocked", "leased", "running", "failed", "abandoned")
        }
        assert state["work"] == expected_work
        assert health["overall"] == "ok"
        assert snap["due"] is False
