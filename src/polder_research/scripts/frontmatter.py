"""frontmatter-fix command."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_spec = importlib.util.spec_from_file_location(
    "_frontmatter_fix",
    _REPO_ROOT / "skills" / "obsidian-knowledgebase-curator" / "scripts" / "frontmatter_fix.py",
)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_frontmatter_fix"] = _mod
_spec.loader.exec_module(_mod)


def cmd_frontmatter_fix(apply: bool = False) -> int:
    if apply:
        sys.argv = ["frontmatter_fix.py", "--apply"]
    else:
        sys.argv = ["frontmatter_fix.py"]
    return _mod.main()
