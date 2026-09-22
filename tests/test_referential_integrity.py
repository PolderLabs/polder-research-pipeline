"""Referential-integrity tests — foreign-key writers must validate parents.

Per AUDIT.md §16: segment.source_id, claim.source_ids, conflict.claim_ids,
evidence-edge claim/source endpoints, and task references must resolve to
existing records before the child is persisted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polder_research import paths as _paths_mod
from polder_research.evidence import (
    assert_record_exists,
    ensure_evidence_dirs,
    register_claim,
    register_conflict,
    register_evidence_edge,
    register_segment,
    register_source,
)
from polder_research.tasks import acquire_lease


MISSING_SRC = "src_00000000-0000-7000-8000-000000000000"
MISSING_CLM = "clm_00000000-0000-7000-8000-000000000000"
MISSING_TSK = "tsk_00000000-0000-7000-8000-000000000000"


@pytest.fixture(autouse=True)
def isolate_research(monkeypatch, tmp_path: Path):
    """Redirect every EVIDENCE_*_DIR and task dir to a fresh tmp directory."""
    research = tmp_path / ".research"
    rewrites = {
        "EVIDENCE_SOURCES_DIR": research / "sources",
        "EVIDENCE_CLAIMS_DIR": research / "claims",
        "EVIDENCE_ENTITIES_DIR": research / "entities",
        "EVIDENCE_SEGMENTS_DIR": research / "segments",
        "EVIDENCE_GAPS_DIR": research / "gaps",
        "EVIDENCE_CONFLICTS_DIR": research / "conflicts",
        "EVIDENCE_EDGES_DIR": research / "edges",
        "RESEARCH_TASKS_DIR": research / "tasks",
        "RESEARCH_LOCKS_DIR": research / "locks",
        "RESEARCH_DIR": research,
    }
    for key, value in rewrites.items():
        monkeypatch.setattr(_paths_mod, key, value, raising=False)
    import polder_research.evidence as _evidence_mod
    import polder_research.tasks as _tasks_mod

    for mod in (_evidence_mod, _tasks_mod):
        for key, value in rewrites.items():
            monkeypatch.setattr(mod, key, value, raising=False)
    yield tmp_path


def _source(tmp_path: Path) -> str:
    return register_source(
        title="T",
        source_type="paper",
        media_type="pdf",
        raw_bytes=b"x",
        repository_root=tmp_path,
    )


class TestSegmentIntegrity:
    def test_missing_source_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        with pytest.raises(ValueError, match="does not exist"):
            register_segment(
                source_id=MISSING_SRC,
                text="passage",
                locator_scheme="paragraph",
                locator_value="1",
                repository_root=tmp_path,
            )

    def test_segment_written_when_source_exists(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        seg = register_segment(
            source_id=src,
            text="passage",
            locator_scheme="paragraph",
            locator_value="1",
            repository_root=tmp_path,
        )
        assert seg.startswith("seg_")


class TestClaimIntegrity:
    def test_missing_source_rejected(self, tmp_path: Path):
        """A claim referencing a non-existent source must raise ValueError."""
        ensure_evidence_dirs(repository_root=tmp_path)
        with pytest.raises(ValueError, match="does not exist"):
            register_claim(
                statement="x",
                source_ids=[MISSING_SRC],
                repository_root=tmp_path,
            )

    def test_one_missing_source_of_many_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        with pytest.raises(ValueError, match="does not exist"):
            register_claim(
                statement="x",
                source_ids=[src, MISSING_SRC],
                repository_root=tmp_path,
            )

    def test_empty_source_ids_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        with pytest.raises(ValueError, match="non-empty"):
            register_claim(statement="x", source_ids=[], repository_root=tmp_path)

    def test_claim_written_when_source_exists(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        clm = register_claim(
            statement="x",
            source_ids=[src],
            repository_root=tmp_path,
        )
        assert clm.startswith("clm_")


class TestConflictIntegrity:
    def test_missing_claim_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        clm = register_claim(statement="A", source_ids=[src], repository_root=tmp_path)
        with pytest.raises(ValueError, match="does not exist"):
            register_conflict(
                claim_ids=[clm, MISSING_CLM],
                repository_root=tmp_path,
            )

    def test_fewer_than_two_claims_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        clm = register_claim(statement="A", source_ids=[src], repository_root=tmp_path)
        with pytest.raises(ValueError, match="at least two"):
            register_conflict(claim_ids=[clm], repository_root=tmp_path)

    def test_duplicate_claim_ids_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        clm = register_claim(statement="A", source_ids=[src], repository_root=tmp_path)
        with pytest.raises(ValueError, match="unique"):
            register_conflict(claim_ids=[clm, clm], repository_root=tmp_path)

    def test_conflict_written_when_claims_exist(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        clm1 = register_claim(statement="A", source_ids=[src], repository_root=tmp_path)
        clm2 = register_claim(statement="B", source_ids=[src], repository_root=tmp_path)
        cfl = register_conflict(claim_ids=[clm1, clm2], repository_root=tmp_path)
        assert cfl.startswith("cfl_")


class TestEvidenceEdgeIntegrity:
    def test_missing_endpoint_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        clm = register_claim(statement="x", source_ids=[src], repository_root=tmp_path)
        with pytest.raises(ValueError, match="does not exist"):
            register_evidence_edge(
                claim_id=clm,
                source_id=MISSING_SRC,
                relation="supports",
                locator={"scheme": "page", "value": "1"},
                repository_root=tmp_path,
            )

    def test_missing_claim_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        with pytest.raises(ValueError, match="does not exist"):
            register_evidence_edge(
                claim_id=MISSING_CLM,
                source_id=src,
                relation="supports",
                locator={"scheme": "page", "value": "1"},
                repository_root=tmp_path,
            )

    def test_edge_written_when_endpoints_exist(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        clm = register_claim(statement="x", source_ids=[src], repository_root=tmp_path)
        evd = register_evidence_edge(
            claim_id=clm,
            source_id=src,
            relation="supports",
            locator={"scheme": "page", "value": "1"},
            repository_root=tmp_path,
        )
        assert evd.startswith("evd_")


class TestLeaseIntegrity:
    def test_missing_task_rejected(self):
        with pytest.raises(ValueError, match="does not exist"):
            acquire_lease(MISSING_TSK, "leaser", 60)

    def test_wrong_prefix_rejected(self):
        with pytest.raises(ValueError, match="expected tsk_ record id"):
            acquire_lease("run_00000000-0000-7000-8000-000000000006", "leaser", 60)


class TestHelperContract:
    def test_returns_parsed_record(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        record = assert_record_exists(
            src,
            prefix="src",
            default_dir=_paths_mod.EVIDENCE_SOURCES_DIR,
            directory_name="sources",
            repository_root=tmp_path,
        )
        assert record["id"] == src
        assert record["title"] == "T"

    def test_bad_prefix_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = _source(tmp_path)
        with pytest.raises(ValueError, match="expected clm_ record id"):
            assert_record_exists(
                src,
                prefix="clm",
                default_dir=_paths_mod.EVIDENCE_CLAIMS_DIR,
                directory_name="claims",
                repository_root=tmp_path,
            )