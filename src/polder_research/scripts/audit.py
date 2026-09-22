"""vault-audit command — wrapped for CLI compatibility."""

from __future__ import annotations

import sys
from pathlib import Path

# ── delegate to the existing standalone script ──────────────────────────────
# The standalone script is kept for backwards compatibility. Import its logic.
_REPO_ROOT = Path(__file__).resolve().parents[3]

import importlib.util  # noqa: E402  (needs _REPO_ROOT computed from __file__ first)

_spec = importlib.util.spec_from_file_location(
    "_vault_audit",
    _REPO_ROOT / "skills" / "obsidian-knowledgebase-curator" / "scripts" / "vault_audit.py",
)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_vault_audit"] = _mod
_spec.loader.exec_module(_mod)


def cmd_vault_audit() -> int:
    """Run vault_audit. Exit code 0 = clean."""
    return _mod.main()
