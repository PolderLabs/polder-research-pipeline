"""frontmatter-fix command."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def cmd_frontmatter_fix(apply: bool = False, repository_root: Path | None = None) -> int:
    root = repository_root or Path.cwd()
    script = root / "skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py"
    if not script.is_file():
        print(f"error: frontmatter-fix requires workspace script: {script}", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("_frontmatter_fix", script)
    if spec is None or spec.loader is None:
        print(f"error: cannot load frontmatter-fix script: {script}", file=sys.stderr)
        return 2
    module = importlib.util.module_from_spec(spec)
    sys.modules["_frontmatter_fix"] = module
    spec.loader.exec_module(module)
    args = ["--root", str(root)]
    if apply:
        args.append("--apply")
    return module.main(args)
