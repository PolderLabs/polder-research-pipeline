"""Maintenance threshold + freshness engine + superseded proxy tests."""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from polder_research.maintenance import (
    build_state,
    derive_stale_records,
    evaluate_maintenance,
    superseded_source_proxy,
    thresholds,
)


MINIMAL_CONFIG = (
    "schema_version: 1\n"
    "task:\n  valid_status:\n    - pending\n    - completed\n"
    "run:\n  valid_status:\n    - draft\n    - active\n"
    "handoff:\n  valid_status:\n    - open\n    - accepted\n"
    "maintenance:\n"
    "  orphan_check_enabled: false\n"
    "  frontmatter_check_enabled: false\n"
    "  broken_link_check_enabled: false\n"
    "  staleness_check_enabled: false\n"
    "  health_compute_interval_hours: 8760\n"
    "  incremental_interval_days: 9999\n"
    "  max_unresolved_duplicates: 9999\n"
    "  max_unresolved_critical_conflicts: 9999\n"
    "  stale_after_days: 30\n"
)


def _scaffold(tmp: Path, *, with_config: str = MINIMAL_CONFIG) -> Path:
    schemas = tmp / "schemas"
    schemas.mkdir()
    for name in (
        "event",
        "task",
        "run",
        "handoff",
        "source",
        "claim",
        "segment",
        "entity",
        "gap",
        "conflict",
        "edge",
    ):
        (schemas / f"{name}.schema.json").write_text(
            '{"$schema":"https://json-schema.org/draft/2020-12/schema",'
            '"type":"object","required":["id","schema_version"],'
            '"additionalProperties":true,'
            '"properties":{"id":{"type":"string"},'
            '"schema_version":{"type":"integer"}}}'
        )
    (tmp / "research.config.yaml").write_text(with_config)
    (tmp / ".research").mkdir()
    return tmp


def test_thresholds_read_from_config(tmp_path: Path):
    _scaffold(tmp_path)
    t = thresholds(tmp_path)
    assert t["incremental_interval_days"] == 9999
    assert t["max_unresolved_duplicates"] == 9999
    assert t["max_unresolved_critical_conflicts"] == 9999
    assert t["stale_after_days"] == 30


def test_thresholds_defaults_when_keys_omitted(tmp_path: Path):
    _scaffold(
        tmp_path,
        with_config=(
            "schema_version: 1\n"
            "task:\n  valid_status: [pending]\n"
            "run:\n  valid_status: [draft]\n"
            "handoff:\n  valid_status: [open]\n"
            "maintenance:\n  orphan_check_enabled: false\n"
            "  frontmatter_check_enabled: false\n"
            "  broken_link_check_enabled: false\n"
            "  staleness_check_enabled: false\n"
            "  health_compute_interval_hours: 24\n"
        ),
    )
    t = thresholds(tmp_path)
    assert t["incremental_interval_days"] is None
    assert t["stale_after_days"] is None


def test_build_state_is_re_exported(tmp_path: Path):
    _scaffold(tmp_path)
    state = build_state(tmp_path)
    # workflow.build_state output contract — has schema_version + work sections.
    assert "schema_version" in state
    assert "work" in state


def test_superseded_source_proxy_returns_lineage_target(tmp_path: Path):
    _scaffold(tmp_path)
    src_dir = tmp_path / ".research" / "sources"
    src_dir.mkdir(parents=True, exist_ok=True)
    canonical = {
        "id": "src_canonical",
        "schema_version": 1,
        "source_status": "current",
        "source_type": "paper",
        "media_type": "pdf",
        "title": "canonical",
        "retrieved_at": "2026-09-22T00:00:00Z",
        "content_sha256": "a" * 64,
    }
    superseded = {
        **canonical,
        "id": "src_superseded",
        "title": "superseded",
        "source_status": "superseded",
        "lineage": [{"relation": "supersedes", "target": "src_canonical"}],
    }
    (src_dir / "src_canonical.json").write_text(json.dumps(canonical))
    (src_dir / "src_superseded.json").write_text(json.dumps(superseded))

    proxy = superseded_source_proxy(superseded, repository_root=tmp_path)
    assert proxy == "src_canonical"


def test_superseded_source_proxy_none_when_no_successor(tmp_path: Path):
    _scaffold(tmp_path)
    src = {
        "id": "src_orphan",
        "schema_version": 1,
        "source_status": "superseded",
        "source_type": "paper",
        "media_type": "pdf",
        "title": "orphan",
        "retrieved_at": "2026-09-22T00:00:00Z",
        "content_sha256": "a" * 64,
        "lineage": [],
    }
    assert superseded_source_proxy(src, repository_root=tmp_path) is None


def test_derive_stale_records_flags_old(tmp_path: Path):
    _scaffold(tmp_path)
    old = datetime(2020, 1, 1, tzinfo=UTC)
    recent = datetime.now(UTC) - timedelta(days=1)
    findings = derive_stale_records(
        [
            {"id": "t_old", "updated_at": old.isoformat().replace("+00:00", "Z")},
            {"id": "t_recent", "updated_at": recent.isoformat().replace("+00:00", "Z")},
        ],
        threshold_days=30,
    )
    ids = {f["id"] for f in findings}
    assert "t_old" in ids
    assert "t_recent" not in ids


def test_derive_stale_records_no_op_when_threshold_none(tmp_path: Path):
    _scaffold(tmp_path)
    assert (
        derive_stale_records(
            [{"id": "t", "updated_at": "2020-01-01T00:00:00Z"}],
            threshold_days=None,
        )
        == []
    )


def test_evaluate_maintenance_exposes_stale_derived_in_inputs(tmp_path: Path):
    repo = _scaffold(tmp_path)
    # Drop a stale source record straight into .research/sources so the
    # schema-validating evidence collection picks it up.
    src_dir = repo / ".research" / "sources"
    src_dir.mkdir(parents=True, exist_ok=True)
    stale = {
        "id": "src_stale",
        "schema_version": 1,
        "source_status": "current",  # declared current, yet chronologically stale
        "source_type": "paper",
        "media_type": "pdf",
        "title": "stale",
        "retrieved_at": "2020-01-01T00:00:00Z",
        "content_sha256": "f" * 64,
        "updated_at": "2020-01-01T00:00:00Z",
    }
    (src_dir / "src_stale.json").write_text(json.dumps(stale))

    snapshot = evaluate_maintenance(repo)
    stale_ids = {f["id"] for f in snapshot["inputs"]["stale_derived"]}
    assert "src_stale" in stale_ids
    names = {t["name"] for t in snapshot["triggers"]}
    assert "stale_derived" in names