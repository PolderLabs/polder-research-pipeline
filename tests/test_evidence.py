"""Tests for evidence primitives — source, claim, entity, gap, conflict, segment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polder_research import evidence as _evidence_mod
from polder_research import paths as _paths_mod
from polder_research.evidence import (
    compute_content_hash,
    ensure_evidence_dirs,
    find_duplicate_source,
    register_claim,
    register_conflict,
    register_entity,
    register_gap,
    register_segment,
    register_source,
)


@pytest.fixture(autouse=True)
def redirect_evidence_dirs(monkeypatch, tmp_path):
    """Redirect EVIDENCE_*_DIR to a temp directory per test.

    Must patch paths_mod (exported name), evidence_mod (local bindings via
    ``from ..paths import``), so the test sees writes to tmp_path instead of
    the real .research/.
    """
    fake_sources = tmp_path / "sources"
    fake_claims = tmp_path / "claims"
    fake_entities = tmp_path / "entities"
    fake_segments = tmp_path / "segments"
    fake_gaps = tmp_path / "gaps"
    fake_conflicts = tmp_path / "conflicts"

    for mod in (_paths_mod, _evidence_mod):
        for k, v in {
            "EVIDENCE_SOURCES_DIR": fake_sources,
            "EVIDENCE_CLAIMS_DIR": fake_claims,
            "EVIDENCE_ENTITIES_DIR": fake_entities,
            "EVIDENCE_SEGMENTS_DIR": fake_segments,
            "EVIDENCE_GAPS_DIR": fake_gaps,
            "EVIDENCE_CONFLICTS_DIR": fake_conflicts,
        }.items():
            monkeypatch.setattr(mod, k, v, raising=False)


def _sources_dir() -> Path:
    """Read the (patched) sources dir live."""
    return _paths_mod.EVIDENCE_SOURCES_DIR


def _claims_dir() -> Path:
    """Read the (patched) claims dir live."""
    return _paths_mod.EVIDENCE_CLAIMS_DIR


class TestComputeContentHash:
    def test_bytes(self):
        h = compute_content_hash(b"hello world")
        assert len(h) == 64
        assert h == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_file(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"test")
        h = compute_content_hash(f)
        assert len(h) == 64


class TestRegisterSource:
    def test_registers_source_with_hash(self):
        ensure_evidence_dirs()
        sid = register_source(
            title="Test Paper",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"hello world",
        )
        assert sid.startswith("src_")
        src_path = _sources_dir() / f"{sid}.json"
        assert src_path.is_file()
        rec = json.loads(src_path.read_text())
        assert rec["title"] == "Test Paper"
        assert (
            rec["content_sha256"]
            == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        )

    def test_find_duplicate_by_doi(self):
        ensure_evidence_dirs()
        sid1 = register_source(
            title="Paper A",
            source_type="paper",
            media_type="pdf",
            doi="10.1234/test",
            raw_bytes=b"a",
        )
        dup = find_duplicate_source(doi="10.1234/test")
        assert dup == sid1

    def test_find_duplicate_by_sha256_no_match(self):
        ensure_evidence_dirs()
        register_source(
            title="Paper A",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"content",
        )
        dup = find_duplicate_source(
            content_sha256="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        )
        assert dup is None


class TestRegisterSegment:
    def test_segment_registers(self):
        ensure_evidence_dirs()
        src_id = register_source(
            title="T",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"x",
        )
        seg_id = register_segment(
            source_id=src_id,
            text="This is a test passage.",
            locator_scheme="paragraph",
            locator_value="1",
        )
        assert seg_id.startswith("seg_")


class TestRegisterClaim:
    def test_registers_claim(self):
        ensure_evidence_dirs()
        src_id = register_source(
            title="T",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"x",
        )
        clm_id = register_claim(
            statement="The sky is blue.",
            source_ids=[src_id],
        )
        assert clm_id.startswith("clm_")


class TestRegisterEntity:
    def test_registers_entity(self):
        ensure_evidence_dirs()
        ent_id = register_entity(name="GPT-4", entity_kind="model")
        assert ent_id.startswith("ent_")


class TestRegisterGap:
    def test_registers_gap(self):
        ensure_evidence_dirs()
        gap_id = register_gap(
            description="What is the latency of GPT-4?",
            priority="high",
        )
        assert gap_id.startswith("gap_")


class TestRegisterConflict:
    def test_registers_conflict(self):
        ensure_evidence_dirs()
        src_id = register_source(
            title="T",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"x",
        )
        clm1 = register_claim(statement="A is true", source_ids=[src_id])
        clm2 = register_claim(statement="A is false", source_ids=[src_id])
        cfl_id = register_conflict(claim_ids=[clm1, clm2])
        assert cfl_id.startswith("cfl_")
