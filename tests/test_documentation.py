"""Tests for P1 documentation — naming conventions, glossary, evidence/provenance models."""

from __future__ import annotations

from pathlib import Path

_HOME = Path(__file__).resolve().parents[1] / "knowledge-base" / "00-home"


def test_home_contains_required_docs():
    """P1: naming-conventions, glossary, evidence-model, provenance-model must exist."""
    for name in ("naming-conventions", "glossary", "evidence-model", "provenance-model"):
        path = _HOME / f"{name}.md"
        assert path.is_file(), f"missing 00-home/{name}.md"


def test_docs_have_frontmatter():
    for name in ("naming-conventions", "glossary", "evidence-model", "provenance-model"):
        path = _HOME / f"{name}.md"
        text = path.read_text()
        assert text.startswith("---\n"), f"{name}.md missing frontmatter"


def test_glossary_canonical_terms():
    text = (_HOME / "glossary.md").read_text()
    # Each canonical term from §AUDIT.md §9 should appear
    for term in (
        "claim",
        "source",
        "evidence",
        "hypothesis",
        "entity",
        "verification",
        "provenance",
        "freshness",
    ):
        assert term.lower() in text.lower(), f"glossary missing term: {term}"


def test_naming_conventions_kebab_case():
    text = (_HOME / "naming-conventions.md").read_text()
    assert "kebab" in text.lower()
    assert "case" in text.lower()


def test_pipelines_brief_exists():
    """P2: project brief lives at 01-project/brief.md."""
    path = Path(__file__).resolve().parents[1] / "knowledge-base" / "01-project" / "brief.md"
    assert path.is_file(), "01-project/brief.md is required by P2"
