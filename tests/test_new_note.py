"""Behavioral tests for new_note — template resolution and Unicode-safe slugs."""

from __future__ import annotations

from pathlib import Path

from polder_research.scripts.new_note import (
    TEMPLATE_BY_KIND,
    cmd_new_note,
    resolve_template,
    slugify,
)
from polder_research.templates import TemplateRegistry


class TestSlugify:
    def test_non_ascii_title_folds_to_ascii(self):
        """NFKD + ASCII fold must turn accented characters into base ASCII.

        Example named in the audit: "Café — Étude" -> "cafe-etude".
        """
        assert slugify("Café — Étude") == "cafe-etude"

    def test_multiple_accents_and_punctuation(self):
        assert slugify("Crème Brûlée & Pâté") == "creme-brulee-pate"

    def test_cjk_falls_back_to_empty_then_underscored(self):
        # Pure non-ASCII text loses every character; caller may then want
        # a stable-ID-backed identity. Slug must not raise.
        assert slugify("東京") == ""

    def test_plain_ascii_unchanged(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_collapses_repeated_separators(self):
        assert slugify("  multiple   spaces  ") == "multiple-spaces"

    def test_digits_and_mixed_case(self):
        assert slugify("Model X 2026 Review") == "model-x-2026-review"


class TestTemplateResolution:
    def test_research_kind_resolves_through_registry(self, repo_root: Path):
        """resolve_template must come from the canonical 99-templates dir."""
        registry = TemplateRegistry(repo_root)
        text = resolve_template("research", template_registry=registry)
        expected = registry.resolve("research-note").text
        assert text == expected

    def test_decision_kind_uses_decision_record_template(self, repo_root: Path):
        registry = TemplateRegistry(repo_root)
        text = resolve_template("decision", template_registry=registry)
        assert text == registry.resolve("decision-record").text

    def test_unknown_kind_falls_back_to_research_note(self, repo_root: Path):
        registry = TemplateRegistry(repo_root)
        text = resolve_template("moc", template_registry=registry)
        assert text == registry.resolve("research-note").text

    def test_every_mapped_template_name_exists(self, repo_root: Path):
        """The kind->template map must not name a missing template file."""
        registry = TemplateRegistry(repo_root)
        names = set(registry.names())
        for kind, name in TEMPLATE_BY_KIND.items():
            assert name in names, f"kind {kind!r} maps to missing template {name!r}"


class TestCmdNewNote:
    def test_dry_run_emits_frontmatter_and_template_body(self, repo_root: Path, capsys):
        rc = cmd_new_note(
            domain="02-research",
            title="Café — Étude",
            dry_run=True,
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "type: research" in out
        assert "status: draft" in out
        assert "# Café — Étude" in out
        # The canonical template body must be present (it contains claim scaffold).
        assert "Observed" in out or "research_question" in out

    def test_rejects_unknown_domain(self, capsys):
        rc = cmd_new_note(domain="07-nope", title="x", dry_run=True)
        assert rc == 2
        assert "unknown domain" in capsys.readouterr().err

    def test_rejects_invalid_type(self, capsys):
        rc = cmd_new_note(domain="02-research", title="x", type_="nope", dry_run=True)
        assert rc == 2
        assert "invalid type" in capsys.readouterr().err

    def test_rejects_invalid_status(self, capsys):
        rc = cmd_new_note(domain="02-research", title="x", status="nope", dry_run=True)
        assert rc == 2
        assert "invalid status" in capsys.readouterr().err
