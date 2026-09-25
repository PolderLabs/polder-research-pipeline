"""vault-audit command — wrapped for CLI compatibility."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from ..paths import BUNDLED_SKILLS_DIR, workspace_script


def cmd_vault_audit(repository_root: Path) -> int:
    """Run vault_audit. Exit code 0 = clean."""
    script = workspace_script(
        "skills/obsidian-knowledgebase-curator/scripts/vault_audit.py", repository_root
    )
    if not script.is_file():
        print(
            f"error: vault-audit script not found: looked in {repository_root} "
            f"and {BUNDLED_SKILLS_DIR}",
            file=sys.stderr,
        )
        return 2
    spec = importlib.util.spec_from_file_location("_vault_audit", script)
    if spec is None or spec.loader is None:
        print(f"error: cannot load vault-audit script: {script}", file=sys.stderr)
        return 2
    module = importlib.util.module_from_spec(spec)
    sys.modules["_vault_audit"] = module
    spec.loader.exec_module(module)
    return module.main(["--root", str(repository_root)])
