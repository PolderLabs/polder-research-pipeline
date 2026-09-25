from __future__ import annotations

import json
from pathlib import Path

import pytest

from polder_research.events import write_event
from polder_research.evidence import (
    acquire_source,
    register_claim,
    register_segment,
    register_source,
)
from polder_research.handoffs import accept_handoff, write_handoff
from polder_research.paths import Workspace
from polder_research.research_methods import _export_path
from polder_research.runs import update_run_status, write_run
from polder_research.schemas import SchemaError, validate
from polder_research.scripts.intake import cmd_intake_register, parse_rows
from polder_research.tasks import acquire_lease, release_lease, update_task_status, write_task


def _intake_workspace(root: Path) -> Path:
    inbox = root / "knowledge-base" / "90-inbox"
    (inbox / "raw").mkdir(parents=True)
    (inbox / "manifest.md").write_text(
        "---\ntype: inbox\nstatus: current\ntags: [intake]\n---\n\n"
        "# Intake Manifest\n\n## Queue\n\n"
        "| Item | Kind | Added | Status | Owner | Outcome |\n"
        "|---|---|---|---|---|---|\n\n## Status lifecycle\n",
        encoding="utf-8",
    )
    return inbox


def test_manifest_dry_run_then_registers_local_and_reference_sources(
    tmp_path: Path, capsys
) -> None:
    inbox = _intake_workspace(tmp_path)
    (inbox / "raw" / "paper.pdf").write_bytes(b"paper bytes")
    manifest = tmp_path / "sources.csv"
    manifest.write_text(
        "title,local_file,canonical_url,source_type,media_type,tags,source_class,notes\n"
        "Paper,paper.pdf,,paper,pdf,primary;recent,first-party,read soon\n"
        "Web reference,,HTTPS://Example.COM/path/#section,webpage,html,triage,vendor,screen later\n"
        "Repeated reference,,https://example.com/path/,webpage,html,triage,,same identity\n",
        encoding="utf-8",
    )

    assert (
        cmd_intake_register(None, manifest=str(manifest), dry_run=True, repository_root=tmp_path)
        == 0
    )
    assert "reuse manifest row 3" in capsys.readouterr().out
    assert not (tmp_path / ".research").exists()
    assert cmd_intake_register(None, manifest=str(manifest), repository_root=tmp_path) == 0

    sources_dir = tmp_path / ".research" / "sources"
    records = [json.loads(path.read_text()) for path in sources_dir.glob("src_*.json")]
    assert len(records) == 2
    local = next(record for record in records if record["title"] == "Paper")
    reference = next(record for record in records if record["title"] == "Web reference")
    assert local["source_class"] == "first-party"
    assert local["tags"] == ["primary", "recent"]
    assert reference["source_status"] == "unacquired"
    assert reference["canonical_url"] == "https://example.com/path"
    assert "content_sha256" not in reference

    assert cmd_intake_register(None, manifest=str(manifest), repository_root=tmp_path) == 0
    assert len(list(sources_dir.glob("src_*.json"))) == 2
    manifest_rows = parse_rows((inbox / "manifest.md").read_text(encoding="utf-8"))
    assert len(manifest_rows) == 3


def test_source_schema_requires_hash_except_for_unacquired(tmp_path: Path) -> None:
    source = {
        "id": "src_00000000-0000-7000-8000-000000000001",
        "schema_version": 1,
        "source_status": "current",
        "source_type": "paper",
        "media_type": "pdf",
        "title": "Paper",
        "retrieved_at": "2026-09-25T00:00:00Z",
    }
    with pytest.raises(SchemaError):
        validate("source", source)

    source.update(source_status="unacquired", canonical_url="https://example.com")
    validate("source", source)
    source["content_sha256"] = "0" * 64
    with pytest.raises(SchemaError):
        validate("source", source)


def test_manifest_invalid_enum_reports_row_before_writing(tmp_path: Path, capsys) -> None:
    _intake_workspace(tmp_path)
    manifest = tmp_path / "sources.jsonl"
    manifest.write_text(
        '{"title":"Bad row","canonical_url":"https://example.com","source_type":"bogus"}\n',
        encoding="utf-8",
    )
    assert cmd_intake_register(None, manifest=str(manifest), repository_root=tmp_path) == 2
    assert "row 1: invalid source_type 'bogus'" in capsys.readouterr().err
    assert not (tmp_path / ".research").exists()


def test_unacquired_source_acquisition_hashes_and_records_event(tmp_path: Path) -> None:
    source_id = register_source(
        title="Reference",
        source_type="webpage",
        media_type="html",
        canonical_url="https://example.com/article",
        source_status="unacquired",
        repository_root=tmp_path,
    )

    acquire_source(source_id, b"downloaded content", repository_root=tmp_path)

    source = json.loads((tmp_path / ".research" / "sources" / f"{source_id}.json").read_text())
    assert source["source_status"] == "current"
    assert len(source["content_sha256"]) == 64
    events = [
        json.loads(path.read_text())
        for path in (tmp_path / ".research" / "events").glob("evt_*.json")
    ]
    assert len(events) == 1
    assert events[0]["event_type"] == "source.acquired"
    assert events[0]["targets"] == [source_id]


def test_unacquired_source_cannot_support_claims_or_segments(tmp_path: Path) -> None:
    source_id = register_source(
        title="Reference",
        source_type="webpage",
        media_type="html",
        canonical_url="https://example.com/article",
        source_status="unacquired",
        repository_root=tmp_path,
    )
    with pytest.raises(ValueError, match="claims require acquired sources"):
        register_claim(
            statement="Claim from unread source",
            source_ids=[source_id],
            repository_root=tmp_path,
        )
    with pytest.raises(ValueError, match="unacquired source"):
        register_segment(
            source_id=source_id,
            text="unread",
            locator_scheme="paragraph",
            locator_value="1",
            repository_root=tmp_path,
        )


def test_workspace_writers_and_export_paths_are_isolated(tmp_path: Path) -> None:
    first = Workspace(tmp_path / "first")
    second = Workspace(tmp_path / "second")
    for workspace in (first, second):
        write_event("source.discovered", "tester", workspace=workspace)
        task_id = write_task("search", "pending", "analyst", "inspect source", workspace=workspace)
        token = acquire_lease(task_id, "reviewer", 60, workspace=workspace)
        release_lease(task_id, token, workspace=workspace)
        update_task_status(task_id, "in_progress", workspace=workspace)
        run_id = write_run({"question": "test"}, workspace=workspace)
        update_run_status(run_id, "active", workspace=workspace)
        handoff_id = write_handoff("analyst", "reviewer", "handoff", workspace=workspace)
        accept_handoff(handoff_id, workspace=workspace)
        assert _export_path("exports/search.csv", workspace=workspace) == (
            workspace.root / "exports" / "search.csv"
        )

    assert len(list(first.research_path("events").glob("evt_*.json"))) == 1
    assert len(list(second.research_path("events").glob("evt_*.json"))) == 1
    assert len(list(first.research_path("tasks").glob("tsk_*.json"))) == 1
    assert len(list(second.research_path("tasks").glob("tsk_*.json"))) == 1
    assert len(list(first.research_path("runs").glob("run_*.json"))) == 1
    assert len(list(second.research_path("handoffs").glob("hnd_*.json"))) == 1
    with pytest.raises(ValueError, match="inside the workspace"):
        _export_path(tmp_path / "outside.csv", workspace=first)
