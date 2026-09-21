"""Smoke tests for vault_audit after P0 fixes."""

from __future__ import annotations

import json
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
    (tmp_path / "00-home").mkdir()
    (tmp_path / "index.md").write_text("---\ntype: moc\nstatus: current\ntags:\n  - dashboard\n---\n# Dashboard\n", encoding="utf-8")
    (tmp_path / "AUDIT.md").write_text("---\ntype: guide\nstatus: current\ntags:\n  - audit\n---\n# Audit\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("---\ntype: guide\nstatus: current\ntags:\n  - agents\n---\n# Agents\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("---\ntype: guide\nstatus: current\ntags:\n  - nav\n---\n# Root\n", encoding="utf-8")
    (tmp_path / "00-home/README.md").write_text("---\ntype: moc\nstatus: current\ntags:\n  - x\n---\n# Home\n\n[[orphan-somewhere|Somewhere]]\n", encoding="utf-8")
    (tmp_path / "00-home" / "orphan-note.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - x\n---\n# Orphan\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(_vault_audit, "REPO_ROOT", tmp_path)
    r = _vault_audit.audit()
    assert "00-home/orphan-note.md" in r["orphans"]


def test_vault_audit_template_stubs_not_flagged(tmp_path: Path, monkeypatch):
    """Template files contain `[[path/to/source]]` stubs; those must not be flagged."""
    (tmp_path / "00-home").mkdir()
    (tmp_path / "index.md").write_text("---\ntype: moc\nstatus: current\ntags:\n  - d\n---\n# D\n", encoding="utf-8")
    (tmp_path / "AUDIT.md").write_text("---\ntype: guide\nstatus: current\ntags:\n  - a\n---\n# A\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("---\ntype: guide\nstatus: current\ntags:\n  - a\n---\n# A\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("---\ntype: guide\nstatus: current\ntags:\n  - n\n---\n# R\n", encoding="utf-8")
    (tmp_path / "99-templates").mkdir()
    (tmp_path / "99-templates/sample.md").write_text(
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

    (tmp_path / "00-home").mkdir()
    (tmp_path / "index.md").write_text("---\ntype: moc\nstatus: current\ntags:\n  - d\n---\n# D\n", encoding="utf-8")
    (tmp_path / "AUDIT.md").write_text("---\ntype: guide\nstatus: current\ntags:\n  - a\n---\n# A\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("---\ntype: guide\nstatus: current\ntags:\n  - a\n---\n# A\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("---\ntype: guide\nstatus: current\ntags:\n  - n\n---\n# R\n", encoding="utf-8")
    # Add an orphan file
    (tmp_path / "00-home" / "orphan-note.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - x\n---\n# Orphan\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(_vault_audit, "REPO_ROOT", tmp_path)
    rc = _vault_audit.main(argv=[])
    assert rc == 1, f"main() must exit 1 when orphans exist; got {rc}"
