"""Tests for events, tasks, runs, handoffs, state builder, health builder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def redirect_research_dirs(monkeypatch, tmp_path):
    """Redirect all .research/ writes to a temp directory per test."""
    from polder_research import paths as _paths_mod
    from polder_research import events as _events_mod
    from polder_research import tasks as _tasks_mod
    from polder_research import runs as _runs_mod
    from polder_research import handoffs as _handoffs_mod
    from polder_research import workflow as _workflow_mod
    from polder_research import maintenance as _maintenance_mod

    fake = tmp_path / ".research"
    paths_map = {
        "RESEARCH_DIR": fake,
        "RESEARCH_STATE": fake / "state.json",
        "RESEARCH_HEALTH": fake / "health.json",
        "RESEARCH_EVENTS_DIR": fake / "events",
        "RESEARCH_TASKS_DIR": fake / "tasks",
        "RESEARCH_RUNS_DIR": fake / "runs",
        "RESEARCH_HANDOFFS_DIR": fake / "handoffs",
        "RESEARCH_MAINTENANCE_DIR": fake / "maintenance",
        "RESEARCH_LOCKS_DIR": fake / "locks",
        "RESEARCH_GENERATED_DIR": fake / "generated",
    }
    for mod in (
        _paths_mod, _events_mod, _tasks_mod, _runs_mod,
        _handoffs_mod, _workflow_mod, _maintenance_mod,
    ):
        for k, v in paths_map.items():
            monkeypatch.setattr(mod, k, v, raising=False)


class TestEvents:
    def test_write_event_creates_record(self):
        from polder_research.events import write_event
        from polder_research.paths import RESEARCH_EVENTS_DIR
        eid = write_event(
            event_type="run.started",
            actor="orchestrator",
            run_id="run_00000000-0000-7000-8000-000000000001",
            summary="started run",
        )
        assert eid.startswith("evt_")
        files = list(RESEARCH_EVENTS_DIR.glob("*.json"))
        assert len(files) == 1
        rec = json.loads(files[0].read_text())
        assert rec["event_type"] == "run.started"
        assert rec["actor"] == "orchestrator"

    def test_event_records_required_fields(self):
        from polder_research.events import write_event
        from polder_research.paths import RESEARCH_EVENTS_DIR
        write_event(
            event_type="task.created",
            actor="acquisition-agent",
            summary="task created",
        )
        rec = json.loads(list(RESEARCH_EVENTS_DIR.glob("*.json"))[0].read_text())
        assert "id" in rec
        assert "timestamp" in rec
        assert "instruction_version" in rec
        assert "code_revision" in rec


class TestTasks:
    def test_write_task_creates_record(self):
        from polder_research.tasks import write_task
        from polder_research.paths import RESEARCH_TASKS_DIR
        tid = write_task(
            task_kind="acquire",
            status="pending",
            role="acquisition-agent",
            summary="Acquire source",
        )
        assert tid.startswith("tsk_")
        rec = json.loads((RESEARCH_TASKS_DIR / f"{tid}.json").read_text())
        assert rec["task_kind"] == "acquire"
        assert rec["status"] == "pending"

    def test_acquire_lease_changes_status(self):
        from polder_research.tasks import write_task, acquire_lease
        from polder_research.paths import RESEARCH_TASKS_DIR
        tid = write_task(
            task_kind="acquire", status="pending",
            role="acquisition-agent", summary="Acquire source",
        )
        token = acquire_lease(tid, leaser="agent-1", ttl_seconds=60)
        assert token.startswith("lse_")
        rec = json.loads((RESEARCH_TASKS_DIR / f"{tid}.json").read_text())
        assert rec["status"] == "leased"
        assert rec["lease"]["leaser"] == "agent-1"

    def test_release_lease_returns_to_pending(self):
        from polder_research.tasks import write_task, acquire_lease, release_lease
        from polder_research.paths import RESEARCH_TASKS_DIR
        tid = write_task(
            task_kind="acquire", status="pending",
            role="acquisition-agent", summary="Acquire source",
        )
        acquire_lease(tid, leaser="agent-1", ttl_seconds=60)
        release_lease(tid)
        rec = json.loads((RESEARCH_TASKS_DIR / f"{tid}.json").read_text())
        assert rec["status"] == "pending"

    def test_update_task_status(self):
        from polder_research.tasks import write_task, update_task_status
        from polder_research.paths import RESEARCH_TASKS_DIR
        tid = write_task(
            task_kind="acquire", status="pending",
            role="acquisition-agent", summary="Acquire source",
        )
        update_task_status(tid, "completed")
        rec = json.loads((RESEARCH_TASKS_DIR / f"{tid}.json").read_text())
        assert rec["status"] == "completed"


class TestRuns:
    def test_write_run_creates_record(self):
        from polder_research.runs import write_run
        from polder_research.paths import RESEARCH_RUNS_DIR
        rid = write_run(
            brief={"question": "What is X?", "scope": "x"},
            run_status="active",
        )
        assert rid.startswith("run_")
        rec = json.loads((RESEARCH_RUNS_DIR / f"{rid}.json").read_text())
        assert rec["run_status"] == "active"
        assert rec["brief"]["question"] == "What is X?"

    def test_update_run_status_records_finished_at(self):
        from polder_research.runs import write_run, update_run_status
        from polder_research.paths import RESEARCH_RUNS_DIR
        rid = write_run(brief={"question": "What is X?"}, run_status="active")
        update_run_status(rid, "completed")
        rec = json.loads((RESEARCH_RUNS_DIR / f"{rid}.json").read_text())
        assert rec["run_status"] == "completed"
        assert rec["finished_at"]


class TestHandoffs:
    def test_write_handoff(self):
        from polder_research.handoffs import write_handoff
        from polder_research.paths import RESEARCH_HANDOFFS_DIR
        hnd = write_handoff(
            from_role="acquisition-agent",
            to_role="pipeline-processing-agent",
            summary="Send for processing",
        )
        assert hnd.startswith("hnd_")
        rec = json.loads((RESEARCH_HANDOFFS_DIR / f"{hnd}.json").read_text())
        assert rec["status"] == "open"

    def test_accept_handoff(self):
        from polder_research.handoffs import write_handoff, accept_handoff
        from polder_research.paths import RESEARCH_HANDOFFS_DIR
        hnd = write_handoff(from_role="a", to_role="b", summary="x")
        accept_handoff(hnd)
        rec = json.loads((RESEARCH_HANDOFFS_DIR / f"{hnd}.json").read_text())
        assert rec["status"] == "accepted"

    def test_reject_handoff_with_reason(self):
        from polder_research.handoffs import write_handoff, reject_handoff
        from polder_research.paths import RESEARCH_HANDOFFS_DIR
        hnd = write_handoff(from_role="a", to_role="b", summary="x")
        reject_handoff(hnd, "insufficient context")
        rec = json.loads((RESEARCH_HANDOFFS_DIR / f"{hnd}.json").read_text())
        assert rec["status"] == "rejected"
        assert rec["rejection_reason"] == "insufficient context"


class TestStateBuilder:
    def test_build_state_runs(self):
        from polder_research.runs import write_run
        from polder_research.workflow import build_state
        write_run(brief={"question": "Q?"}, run_status="active")
        write_run(brief={"question": "Q2?"}, run_status="completed")
        state = build_state()
        assert state["runs"]["total"] == 2
        assert state["runs"]["by_status"]["active"] == 1
        assert state["runs"]["by_status"]["completed"] == 1

    def test_build_state_events(self):
        from polder_research.events import write_event
        from polder_research.workflow import build_state
        write_event(event_type="run.started", actor="orchestrator")
        write_event(event_type="task.created", actor="acquisition-agent")
        write_event(event_type="task.completed", actor="acquisition-agent")
        state = build_state()
        assert state["events"]["total"] == 3

    def test_save_state_persists(self):
        from polder_research.runs import write_run
        from polder_research.workflow import build_state, save_state
        from polder_research.paths import RESEARCH_STATE
        write_run(brief={"question": "Q"}, run_status="active")
        save_state()
        assert RESEARCH_STATE.is_file()
        rec = json.loads(RESEARCH_STATE.read_text())
        assert rec["schema_version"] == 1
        assert rec["runs"]["total"] == 1


class TestHealthBuilder:
    def test_build_health_overall_ok_when_no_issues(self):
        from polder_research.maintenance import build_health
        health = build_health()
        assert health["overall"] in ("ok", "degraded")

    def test_save_health_persists(self):
        from polder_research.maintenance import save_health
        from polder_research.paths import RESEARCH_HEALTH
        save_health()
        assert RESEARCH_HEALTH.is_file()
