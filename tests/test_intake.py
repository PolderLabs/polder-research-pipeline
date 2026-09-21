"""Tests for intake_register — P0 defect fixes (AUDIT.md §3.5-3.9)."""

from __future__ import annotations

import re

import pytest

from polder_research.scripts.intake import (
    _find_row,
    parse_rows,
    VALID_KIND,
    VALID_STATUS,
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
