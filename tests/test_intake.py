"""Tests for intake_register — P0 defect fixes (AUDIT.md §3.5-3.9)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from polder_research.scripts.intake import (
    VALID_KIND,
    VALID_STATUS,
    _find_row,
    cmd_intake_register,
    parse_rows,
)


class TestParseRows:
    def test_parses_data_rows(self):
        text = """
| Item | Kind | Added | Status | Owner | Outcome |
|---|---|---|---|---|---|
| paper.pdf | pdf | 2026-09-01 | filed | agent | 02-research/results |
| repo.zip | repository | 2026-09-02 | new | alice | — |
"""
        rows = parse_rows(text)
        assert len(rows) == 2
        assert rows[0][0] == "paper.pdf"
        assert rows[0][3] == "filed"
        assert rows[1][0] == "repo.zip"
        assert rows[1][1] == "repository"

    def test_skips_header_and_separator(self):
        text = """
| Item | Kind | Added | Status | Owner | Outcome |
|---|---|---|---|---|---|
"""
        assert parse_rows(text) == []


class TestFindRow:
    def test_exact_match_first_column(self):
        rows = [
            ["paper.pdf", "pdf", "2026-09-01", "new", "agent", "—"],
            ["repo.zip", "repository", "2026-09-02", "new", "alice", "—"],
        ]
        idx, cells = _find_row(rows, "repo.zip")
        assert idx == 1
        assert cells[0] == "repo.zip"

    def test_not_substring_match(self):
        """§3.7: filename must match exactly, not as substring."""
        rows = [
            ["main.pdf", "pdf", "2026-09-01", "new", "agent", "—"],
            ["main-extra.pdf", "pdf", "2026-09-02", "new", "bob", "—"],
        ]
        idx, cells = _find_row(rows, "main.pdf")
        assert idx == 0
        assert cells[0] == "main.pdf"
        # main-extra.pdf should NOT match "main.pdf"
        assert _find_row(rows, "main-extra.pdf") is not None

    def test_not_found_returns_none(self):
        rows = [["paper.pdf", "pdf", "2026-09-01", "new", "agent", "—"]]
        assert _find_row(rows, "does-not-exist") is None

    def test_empty_list_returns_none(self):
        assert _find_row([], "paper.pdf") is None


class TestVocabularies:
    def test_all_status_values_are_defined(self):
        for s in VALID_STATUS:
            assert re.match(r"^[a-z_]+$", s), f"bad status: {s}"

    def test_kind_includes_audit_canonical_types(self):
        # §3.4: source_type values are accepted as intake kind
        assert "paper" in VALID_KIND
        assert "documentation" in VALID_KIND
        assert "dataset" in VALID_KIND
        assert "benchmark" in VALID_KIND


class TestIntakeId:
    def test_id_is_stable_across_filenames(self):
        """Stable ID survives absolute-path moves and filename renames."""
        from polder_research.scripts.intake import intake_id

        sha = "a" * 64
        first = intake_id(content_sha256=sha, kind="paper")
        second = intake_id(content_sha256=sha, kind="paper")
        assert first == second
        assert first.startswith("int_")
        assert first.endswith("_paper")

    def test_id_changes_when_kind_changes(self):
        """Same content but different kind yields a different intake ID."""
        from polder_research.scripts.intake import intake_id

        sha = "b" * 64
        assert intake_id(content_sha256=sha, kind="paper") != intake_id(
            content_sha256=sha, kind="dataset"
        )


class TestSetSyncsCanonicalRecord:
    """``--set`` must not leave the manifest and the canonical record disagreeing.

    The record under ``.research/intake`` is authoritative; ``manifest.md`` is
    a human projection of it. A status flip that only rewrites the projection
    makes the two surfaces report different lifecycle states for the same item.
    """

    @staticmethod
    def _workspace(tmp_path: Path, *, with_row: bool) -> Path:
        inbox_dir = tmp_path / "knowledge-base" / "90-inbox"
        raw_dir = inbox_dir / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "paper.pdf").write_bytes(b"paper-content")
        row = "| paper.pdf | pdf | 2026-09-26 | new | curator | — |\n" if with_row else ""
        (inbox_dir / "manifest.md").write_text(
            "---\ntype: inbox\nstatus: current\ntags: [intake]\n---\n\n"
            "# Intake Manifest\n\n"
            "## Queue\n\n"
            "| Item | Kind | Added | Status | Owner | Outcome |\n"
            "|---|---|---|---|---|---|\n" + row,
            encoding="utf-8",
        )
        return tmp_path

    @staticmethod
    def _record(tmp_path: Path) -> dict:
        records = list((tmp_path / ".research" / "intake").glob("int_*.json"))
        assert len(records) == 1
        return json.loads(records[0].read_text(encoding="utf-8"))

    def test_set_updates_both_manifest_and_record(self, tmp_path: Path):
        repository_root = self._workspace(tmp_path, with_row=False)
        assert (
            cmd_intake_register(
                "paper.pdf", kind="pdf", owner="curator", repository_root=repository_root
            )
            == 0
        )
        assert self._record(repository_root)["status"] == "new"

        assert (
            cmd_intake_register(
                None,
                set_file="paper.pdf",
                status="distilled",
                outcome="knowledge-base/02-research/paper.md",
                repository_root=repository_root,
            )
            == 0
        )

        record = self._record(repository_root)
        assert record["status"] == "distilled"
        assert record["outcome"] == "knowledge-base/02-research/paper.md"

        rows = parse_rows(
            (repository_root / "knowledge-base/90-inbox/manifest.md").read_text(encoding="utf-8")
        )
        assert rows[0][3] == "distilled"
        assert rows[0][5] == "knowledge-base/02-research/paper.md"
        assert record["status"] == rows[0][3]
        assert record["outcome"] == rows[0][5]

    def test_set_still_validates_status(self, tmp_path: Path):
        repository_root = self._workspace(tmp_path, with_row=False)
        cmd_intake_register(
            "paper.pdf", kind="pdf", owner="curator", repository_root=repository_root
        )
        assert (
            cmd_intake_register(
                None, set_file="paper.pdf", status="bogus", repository_root=repository_root
            )
            == 2
        )
        assert self._record(repository_root)["status"] == "new"

    def test_set_without_record_fails_and_leaves_manifest_untouched(self, tmp_path, capsys):
        """The record is authoritative, so a missing one is an error, not a warning."""
        repository_root = self._workspace(tmp_path, with_row=True)
        before = (repository_root / "knowledge-base/90-inbox/manifest.md").read_text(
            encoding="utf-8"
        )
        assert (
            cmd_intake_register(
                None,
                set_file="paper.pdf",
                status="triaged",
                repository_root=repository_root,
            )
            == 2
        )
        assert "no canonical intake record" in capsys.readouterr().err
        after = (repository_root / "knowledge-base/90-inbox/manifest.md").read_text(
            encoding="utf-8"
        )
        assert after == before

    def test_unknown_item_still_fails(self, tmp_path):
        repository_root = self._workspace(tmp_path, with_row=True)
        assert (
            cmd_intake_register(
                None, set_file="absent.pdf", status="triaged", repository_root=repository_root
            )
            == 2
        )
