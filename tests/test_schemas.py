"""Tests for the schema registry and JSON schemas."""

from __future__ import annotations

from pathlib import Path

import pytest

from polder_research.schemas import SCHEMAS, get, validate, SchemaError


class TestSchemaRegistry:
    def test_all_expected_schemas_loaded(self):
        expected = {
            "source", "claim", "entity", "event",
            "task", "run", "handoff", "decision",
            "segment", "conflict", "gap",
        }
        assert expected.issubset(SCHEMAS.keys()), f"missing: {expected - SCHEMAS.keys()}"

    def test_get_returns_dict(self):
        src = get("source")
        assert isinstance(src, dict)
        assert "$schema" in src

    def test_get_unknown_raises_keyerror(self):
        with pytest.raises(KeyError):
            get("does-not-exist")

    def test_validate_source_minimal(self):
        validate("source", {
            "id": "src_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "source_status": "current",
            "source_type": "paper",
            "media_type": "pdf",
            "title": "Test",
            "retrieved_at": "2026-09-22T00:00:00Z",
            "content_sha256": "a" * 64,
        })

    def test_validate_source_invalid_type(self):
        with pytest.raises(SchemaError):
            validate("source", {
                "id": "src_00000000-0000-7000-8000-000000000001",
                "schema_version": 1,
                "source_status": "current",
                "source_type": "not-a-type",
                "media_type": "pdf",
                "title": "Test",
                "retrieved_at": "2026-09-22T00:00:00Z",
                "content_sha256": "a" * 64,
            })

    def test_validate_task_minimal(self):
        validate("task", {
            "id": "tsk_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "task_kind": "acquire",
            "status": "pending",
            "role": "acquisition-agent",
            "created_at": "2026-09-22T00:00:00Z",
            "summary": "Test task",
        })

    def test_validate_run_minimal(self):
        validate("run", {
            "id": "run_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "run_status": "draft",
            "created_at": "2026-09-22T00:00:00Z",
            "brief": {"question": "What?"},
        })

    def test_validate_handoff_minimal(self):
        validate("handoff", {
            "id": "hnd_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "from_role": "acquisition-agent",
            "to_role": "pipeline-processing-agent",
            "status": "open",
            "created_at": "2026-09-22T00:00:00Z",
            "summary": "handoff",
        })

    def test_validate_claim_minimal(self):
        validate("claim", {
            "id": "clm_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "statement": "Test claim",
            "claim_status": "draft",
            "created_at": "2026-09-22T00:00:00Z",
            "source_ids": ["src_00000000-0000-7000-8000-000000000001"],
        })

    def test_validate_entity_minimal(self):
        validate("entity", {
            "id": "ent_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "name": "GPT-4",
            "entity_kind": "model",
            "created_at": "2026-09-22T00:00:00Z",
        })

    def test_validate_gap_minimal(self):
        validate("gap", {
            "id": "gap_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "description": "Test gap",
            "status": "open",
            "created_at": "2026-09-22T00:00:00Z",
        })

    def test_validate_conflict_minimal(self):
        validate("conflict", {
            "id": "cfl_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "claim_ids": [
                "clm_00000000-0000-7000-8000-000000000001",
                "clm_00000000-0000-7000-8000-000000000002",
            ],
            "status": "open",
            "created_at": "2026-09-22T00:00:00Z",
        })

    def test_validate_segment_minimal(self):
        validate("segment", {
            "id": "seg_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "source_id": "src_00000000-0000-7000-8000-000000000001",
            "text": "Test passage",
            "locator": {"scheme": "paragraph"},
        })

    def test_validate_event_minimal(self):
        validate("event", {
            "id": "evt_00000000-0000-7000-8000-000000000001",
            "event_type": "run.started",
            "actor": "orchestrator",
            "timestamp": "2026-09-22T00:00:00Z",
            "instruction_version": "0.1.0",
            "code_revision": "abc123",
        })

    def test_validate_decision_minimal(self):
        validate("decision", {
            "id": "dec_00000000-0000-7000-8000-000000000001",
            "schema_version": 1,
            "title": "Use JSON schemas",
            "decision_status": "accepted",
            "created_at": "2026-09-22T00:00:00Z",
            "summary": "Decision summary",
        })
