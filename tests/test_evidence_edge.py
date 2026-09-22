"""Behavioral tests for the evidence-edge record and intake canonical-source
integration.

Isolates .research paths through the ``repository_root`` argument.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polder_research import paths as _paths_mod
from polder_research.evidence import (
    compute_content_hash,
    ensure_evidence_dirs,
    register_claim,
    register_evidence_edge,
    register_segment,
    register_source,
)
from polder_research.scripts.intake import (
    canonical_source_for_raw,
    cmd_intake_register,
    parse_rows,
)


@pytest.fixture(autouse=True)
def isolate_research(monkeypatch, tmp_path: Path):
    """Redirect every EVIDENCE_*_DIR to a fresh tmp directory per test.

    Mirrors the in-package rule that all records live under
    ``<repository_root>/.research/<kind>``.
    """
    research = tmp_path / ".research"
    rewrites = {
        "EVIDENCE_SOURCES_DIR": research / "sources",
        "EVIDENCE_CLAIMS_DIR": research / "claims",
        "EVIDENCE_ENTITIES_DIR": research / "entities",
        "EVIDENCE_SEGMENTS_DIR": research / "segments",
        "EVIDENCE_GAPS_DIR": research / "gaps",
        "EVIDENCE_CONFLICTS_DIR": research / "conflicts",
        "EVIDENCE_EDGES_DIR": research / "edges",
        "RESEARCH_DIR": research,
    }
    for key, value in rewrites.items():
        monkeypatch.setattr(_paths_mod, key, value, raising=False)
    yield tmp_path


@pytest.fixture
def inbox(tmp_path: Path) -> Path:
    inbox_dir = tmp_path / "90-inbox"
    raw_dir = inbox_dir / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "first.pdf").write_bytes(b"first-content")
    (raw_dir / "second.pdf").write_bytes(b"second-content")
    manifest = inbox_dir / "manifest.md"
    manifest.write_text(
        "---\ntype: inbox\nstatus: current\ntags: [intake]\n---\n\n"
        "# Intake Manifest\n\n"
        "## Queue\n\n"
        "| Item | Kind | Added | Status | Owner | Outcome |\n"
        "|---|---|---|---|---|---|\n\n"
        "## Status lifecycle\n",
        encoding="utf-8",
    )
    return inbox_dir

    def test_segment_belongs_to_source(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src1 = register_source(
            title="A",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"a",
            repository_root=tmp_path,
        )
        src2 = register_source(
            title="B",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"b",
            repository_root=tmp_path,
        )
        seg = register_segment(
            source_id=src1,
            text="verbatim",
            locator_scheme="paragraph",
            locator_value="3",
            repository_root=tmp_path,
        )
        clm = register_claim(
            statement="x",
            source_ids=[src1],
            repository_root=tmp_path,
        )
        with pytest.raises(ValueError, match="does not belong"):
            register_evidence_edge(
                claim_id=clm,
                source_id=src2,
                relation="supports",
                segment_id=seg,
                repository_root=tmp_path,
            )

    def test_invalid_relation_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = register_source(
            title="A",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"a",
            repository_root=tmp_path,
        )
        clm = register_claim(
            statement="x",
            source_ids=[src],
            repository_root=tmp_path,
        )
        with pytest.raises(ValueError, match="relation"):
            register_evidence_edge(
                claim_id=clm,
                source_id=src,
                relation="mentions",
                locator={"scheme": "page", "value": "1"},
                repository_root=tmp_path,
            )

    def test_missing_endpoint_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        with pytest.raises(ValueError, match="record does not exist"):
            register_evidence_edge(
                claim_id="clm_does-not-exist",
                source_id="src_does-not-exist",
                relation="supports",
                locator={"scheme": "page", "value": "1"},
                repository_root=tmp_path,
            )

    def test_locator_required(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = register_source(
            title="A",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"a",
            repository_root=tmp_path,
        )
        clm = register_claim(
            statement="x",
            source_ids=[src],
            repository_root=tmp_path,
        )
        with pytest.raises(ValueError, match="segment_id or locator"):
            register_evidence_edge(
                claim_id=clm,
                source_id=src,
                relation="supports",
                repository_root=tmp_path,
            )

    def test_locator_scheme_invalid_rejected(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = register_source(
            title="A",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"a",
            repository_root=tmp_path,
        )
        clm = register_claim(
            statement="x",
            source_ids=[src],
            repository_root=tmp_path,
        )
        with pytest.raises(ValueError, match="locator requires a valid scheme"):
            register_evidence_edge(
                claim_id=clm,
                source_id=src,
                relation="supports",
                locator={"scheme": "nonsense"},
                repository_root=tmp_path,
            )

    def test_edge_persists_and_resolves_endpoints(self, tmp_path: Path):
        ensure_evidence_dirs(repository_root=tmp_path)
        src = register_source(
            title="A",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"a",
            repository_root=tmp_path,
        )
        seg = register_segment(
            source_id=src,
            text="verbatim",
            locator_scheme="page",
            locator_value="3",
            repository_root=tmp_path,
        )
        clm = register_claim(
            statement="x",
            source_ids=[src],
            repository_root=tmp_path,
        )
        evd = register_evidence_edge(
            claim_id=clm,
            source_id=src,
            relation="supports",
            segment_id=seg,
            directness="primary",
            confidence="high",
            repository_root=tmp_path,
        )
        assert evd.startswith("evd_")
        record = json.loads((_paths_mod.EVIDENCE_EDGES_DIR / f"{evd}.json").read_text())
        assert record["claim_id"] == clm
        assert record["source_id"] == src
        assert record["segment_id"] == seg
        assert record["relation"] == "supports"
        assert record["directness"] == "primary"
        assert record["confidence"] == "high"
        assert record["locator"]["scheme"] == "page"
        assert record["locator"]["value"] == "3"

    def test_edge_locators_are_validated_against_schema(self, tmp_path: Path):
        from polder_research.schemas import validate

        ensure_evidence_dirs(repository_root=tmp_path)
        src = register_source(
            title="A",
            source_type="paper",
            media_type="pdf",
            raw_bytes=b"a",
            repository_root=tmp_path,
        )
        clm = register_claim(
            statement="x",
            source_ids=[src],
            repository_root=tmp_path,
        )
        evd = register_evidence_edge(
            claim_id=clm,
            source_id=src,
            relation="contradicts",
            locator={"scheme": "section", "value": "5.2"},
            directness="secondary",
            confidence="medium",
            repository_root=tmp_path,
        )
        record = json.loads((_paths_mod.EVIDENCE_EDGES_DIR / f"{evd}.json").read_text())
        validate("evidence", record)


class TestIntakeCanonicalSource:
    def test_register_creates_one_source_one_row(self, inbox, tmp_path):
        repository_root = tmp_path
        source_id = canonical_source_for_raw(
            "first.pdf",
            kind="pdf",
            repository_root=repository_root,
        )
        assert source_id.startswith("src_")
        sources = list(_paths_mod.EVIDENCE_SOURCES_DIR.glob("src_*.json"))
        assert len(sources) == 1

        rc = cmd_intake_register(
            file="first.pdf",
            kind="pdf",
            repository_root=repository_root,
        )
        assert rc == 0
        rows = parse_rows((repository_root / "90-inbox/manifest.md").read_text())
        assert len(rows) == 1
        assert rows[0][0] == "first.pdf"

        record = json.loads(sources[0].read_text())
        assert record["content_sha256"] == compute_content_hash(b"first-content")
        assert record["raw_location"] == "90-inbox/raw/first.pdf"

    def test_re_register_is_idempotent(self, inbox, tmp_path):
        repository_root = tmp_path
        first = canonical_source_for_raw(
            "first.pdf",
            kind="pdf",
            repository_root=repository_root,
        )
        cmd_intake_register(
            file="first.pdf",
            kind="pdf",
            repository_root=repository_root,
        )
        # Re-register same file with same kind.
        second = canonical_source_for_raw(
            "first.pdf",
            kind="pdf",
            repository_root=repository_root,
        )
        cmd_intake_register(
            file="first.pdf",
            kind="pdf",
            repository_root=repository_root,
        )
        assert first == second
        sources = list(_paths_mod.EVIDENCE_SOURCES_DIR.glob("src_*.json"))
        assert len(sources) == 1
        rows = parse_rows((repository_root / "90-inbox/manifest.md").read_text())
        assert len(rows) == 1

    def test_missing_raw_file_does_not_register(self, tmp_path):
        (tmp_path / "90-inbox" / "raw").mkdir(parents=True)
        (tmp_path / "90-inbox" / "manifest.md").write_text(
            "| Item | Kind | Added | Status | Owner | Outcome |\n|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="raw item not found"):
            canonical_source_for_raw(
                "ghost.pdf",
                kind="pdf",
                repository_root=tmp_path,
            )
        rows = parse_rows((tmp_path / "90-inbox/manifest.md").read_text())
        assert rows == []
        sources = list(_paths_mod.EVIDENCE_SOURCES_DIR.glob("src_*.json"))
        assert sources == []

    def test_source_registration_failure_leaves_no_manifest_row(self, tmp_path):
        (tmp_path / "90-inbox" / "raw").mkdir(parents=True)
        (tmp_path / "90-inbox" / "manifest.md").write_text(
            "| Item | Kind | Added | Status | Owner | Outcome |\n|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
        rc = cmd_intake_register(
            file="ghost.pdf",
            kind="pdf",
            repository_root=tmp_path,
        )
        assert rc == 2
        rows = parse_rows((tmp_path / "90-inbox/manifest.md").read_text())
        assert rows == []

    def test_kind_drives_source_type(self, inbox, tmp_path):
        repository_root = tmp_path
        canonical_source_for_raw(
            "second.pdf",
            kind="article",
            repository_root=repository_root,
        )
        sources = list(_paths_mod.EVIDENCE_SOURCES_DIR.glob("src_*.json"))
        assert len(sources) == 1
        record = json.loads(sources[0].read_text())
        assert record["source_type"] == "article"
        assert record["media_type"] == "pdf"
        assert record["title"] == "second.pdf"
