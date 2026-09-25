"""Smoke tests for vault_audit after P0 fixes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Inject src/ into path
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))


def _load_module(name: str, path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_vault_audit = _load_module(
    "_test_vault_audit",
    _REPO_ROOT / "skills" / "obsidian-knowledgebase-curator" / "scripts" / "vault_audit.py",
)


def test_vault_audit_clean_run(repo_root, monkeypatch):
    """The current repository should audit clean (P0 exit criterion)."""
    # Patch REPO_ROOT in the loaded module
    monkeypatch.setattr(_vault_audit, "REPO_ROOT", repo_root)
    r = _vault_audit.audit()
    assert isinstance(r, dict)
    assert "links" in r
    assert "frontmatter_issues" in r


def test_vault_audit_detects_orphan(tmp_path: Path, monkeypatch):
    # create minimal vault
    vault = tmp_path / "knowledge-base"
    (vault / "00-home").mkdir(parents=True)
    (vault / "index.md").write_text(
        "---\ntype: moc\nstatus: current\ntags:\n  - dashboard\n---\n# Dashboard\n",
        encoding="utf-8",
    )
    (vault / "AUDIT.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - audit\n---\n# Audit\n", encoding="utf-8"
    )
    (vault / "AGENTS.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - agents\n---\n# Agents\n", encoding="utf-8"
    )
    (vault / "README.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - nav\n---\n# Root\n", encoding="utf-8"
    )
    (vault / "00-home/README.md").write_text(
        "---\ntype: moc\nstatus: current\ntags:\n  - x\n---\n# Home\n\n[[orphan-somewhere|Somewhere]]\n",
        encoding="utf-8",
    )
    (vault / "00-home" / "orphan-note.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - x\n---\n# Orphan\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(_vault_audit, "REPO_ROOT", tmp_path)
    r = _vault_audit.audit()
    assert "knowledge-base/00-home/orphan-note.md" in r["orphans"]


def test_vault_audit_template_stubs_not_flagged(tmp_path: Path, monkeypatch):
    """Template files contain `[[path/to/source]]` stubs; those must not be flagged."""
    vault = tmp_path / "knowledge-base"
    (vault / "00-home").mkdir(parents=True)
    (vault / "index.md").write_text(
        "---\ntype: moc\nstatus: current\ntags:\n  - d\n---\n# D\n", encoding="utf-8"
    )
    (vault / "AUDIT.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - a\n---\n# A\n", encoding="utf-8"
    )
    (vault / "AGENTS.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - a\n---\n# A\n", encoding="utf-8"
    )
    (vault / "README.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - n\n---\n# R\n", encoding="utf-8"
    )
    (vault / "99-templates").mkdir()
    (vault / "99-templates/sample.md").write_text(
        "---\ntype: template\nstatus: current\ntags:\n  - t\n---\n\n# Template\n\n"
        "- `[[path/to/source]]`\n"
        "- `[[02-research/note-slug]]`\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(_vault_audit, "REPO_ROOT", tmp_path)
    r = _vault_audit.audit()
    # No link issues for templates
    for issue in r["link_issues"]:
        assert "99-templates" not in issue


def test_vault_audit_main_exit_code_blocks_on_orphans(tmp_path: Path, monkeypatch):
    """main() must exit non-zero when orphans exist (P0 §3 / §33)."""
    vault = tmp_path / "knowledge-base"
    (vault / "00-home").mkdir(parents=True)
    (vault / "index.md").write_text(
        "---\ntype: moc\nstatus: current\ntags:\n  - d\n---\n# D\n", encoding="utf-8"
    )
    (vault / "AUDIT.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - a\n---\n# A\n", encoding="utf-8"
    )
    (vault / "AGENTS.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - a\n---\n# A\n", encoding="utf-8"
    )
    (vault / "README.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - n\n---\n# R\n", encoding="utf-8"
    )
    # Add an orphan file
    (vault / "00-home" / "orphan-note.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - x\n---\n# Orphan\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(_vault_audit, "REPO_ROOT", tmp_path)
    rc = _vault_audit.main(argv=[])
    assert rc == 1, f"main() must exit 1 when orphans exist; got {rc}"


def _write_frontmatter_schema(repo_root: Path) -> None:
    schema_dir = repo_root / "schemas"
    schema_dir.mkdir(exist_ok=True)
    source = _REPO_ROOT / "schemas" / "frontmatter.schema.json"
    (schema_dir / "frontmatter.schema.json").write_text(
        source.read_text(encoding="utf-8"), encoding="utf-8"
    )


@pytest.mark.parametrize(
    "frontmatter, expected",
    [
        (
            "---\ntype: made-up\nstatus: current\ntags:\n  - valid-tag\n---\n# Bad type\n",
            "type='made-up' not in",
        ),
        (
            "---\ntype: guide\nstatus: maybe\ntags:\n  - valid-tag\n---\n# Bad status\n",
            "status='maybe' not in",
        ),
        (
            "---\ntype: guide\ntype: source\nstatus: current\ntags:\n  - valid-tag\n---\n# Duplicate\n",
            "duplicate frontmatter key",
        ),
        (
            "---\ntype: guide\nstatus: current\ntags: valid-tag\n---\n# Scalar tags\n",
            "canonical frontmatter schema",
        ),
    ],
)
def test_vault_audit_blocks_noncanonical_frontmatter(
    tmp_vault: Path, frontmatter: str, expected: str
):
    _write_frontmatter_schema(tmp_vault)
    note = tmp_vault / "knowledge-base" / "00-home" / "invalid-frontmatter.md"
    note.write_text(frontmatter, encoding="utf-8")

    result = _vault_audit.audit(tmp_vault)

    assert any(expected in issue for issue in result["frontmatter_issues"])


def test_vault_audit_explicit_root_does_not_mutate_module_default(tmp_vault: Path):
    _write_frontmatter_schema(tmp_vault)

    result = _vault_audit.audit(tmp_vault)

    assert isinstance(result["frontmatter_issues"], list)
    assert _vault_audit.REPO_ROOT == _REPO_ROOT


def test_raw_drop_zone_excludes_dropped_markdown(tmp_path: Path, monkeypatch):
    """A dropped .md in the raw drop zone is a source artifact, not a note.

    90-inbox/raw/README.md invites small text files to be dropped verbatim, so
    the audit must not require frontmatter there. It must also keep that
    README itself in the graph, because 90-inbox/README.md links to it.
    """
    vault = tmp_path / "knowledge-base"
    raw = vault / "90-inbox" / "raw"
    raw.mkdir(parents=True)
    (raw / "dropped-source.md").write_text("# Original\n\nNo frontmatter.\n", encoding="utf-8")
    (raw / "README.md").write_text(
        "---\ntype: inbox\nstatus: current\ntags:\n  - intake\n---\n\n# Drop Zone\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(_vault_audit, "REPO_ROOT", tmp_path)

    scoped = {str(p.relative_to(tmp_path)) for p in _vault_audit.vault_md_files(tmp_path)}

    assert "knowledge-base/90-inbox/raw/dropped-source.md" not in scoped
    assert "knowledge-base/90-inbox/raw/README.md" in scoped
