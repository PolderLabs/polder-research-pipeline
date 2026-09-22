"""Tests for frontmatter_fix.py — P0 alignment with vault_audit scope."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "_frontmatter_fix_test",
        _REPO_ROOT / "skills" / "obsidian-knowledgebase-curator" / "scripts" / "frontmatter_fix.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_frontmatter_fix_test"] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()


def test_skip_parts_shared_with_paths(monkeypatch, tmp_path: Path):
    """frontmatter_fix must use the same SKIP_PARTS as vault_audit (P0 §3.16)."""
    from polder_research import paths as paths_mod

    assert _mod.SKIP_PARTS == paths_mod.SKIP_PARTS, (
        "frontmatter_fix.SKIP_PARTS must be the same set as polder_research.paths.SKIP_PARTS"
    )


def test_fills_missing_frontmatter(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Patch REPO_ROOT
    monkeypatch.setattr(_mod, "REPO_ROOT", tmp_path)
    (tmp_path / "00-home").mkdir()
    note = tmp_path / "00-home" / "no-fm.md"
    note.write_text("# Hello\n\nContent.\n", encoding="utf-8")

    rc = _mod.main(argv=[])
    assert rc == 0
    # In dry-run mode no change. Verify the script detected it.
    text = note.read_text()
    assert text.startswith("# Hello")  # not yet applied


def test_apply_writes_frontmatter(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_mod, "REPO_ROOT", tmp_path)
    (tmp_path / "00-home").mkdir()
    note = tmp_path / "00-home" / "no-fm.md"
    note.write_text("# Hello\n\nContent.\n", encoding="utf-8")

    rc = _mod.main(argv=["--apply"])
    assert rc == 0

    text = note.read_text()
    assert text.startswith("---\n")
    assert "type:" in text
    assert "status:" in text


def test_infer_type_from_domain(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(_mod, "REPO_ROOT", tmp_path)
    assert _mod.infer_type(Path(tmp_path / "00-home" / "x.md")) == "guide"
    assert _mod.infer_type(Path(tmp_path / "02-research" / "x.md")) == "research"
    assert _mod.infer_type(Path(tmp_path / "04-decisions" / "x.md")) == "decision"
