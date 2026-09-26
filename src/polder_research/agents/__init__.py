"""Agent role manifests — read-only registry for agent capabilities and metadata.

Loads the canonical role manifests under ``agents/roles/*.yaml`` (via
``polder_research.paths.AGENTS_DIR``) and exposes runtime helpers used by the
control-plane writers:

- ``get_instruction_version(role)`` — manifest-declared instruction version.
- ``get_code_revision()`` — current git revision (fallback ``"unknown"``).
- ``role_can(role, action)`` — fail-closed allow-list check over ``tools``.
- ``require_role(role, action)`` — ``role_can`` that raises PermissionError.

The YAML structure of the manifests is intentionally flat (top-level scalars
and one-level lists), so a small built-in parser is used; PyYAML is not a
runtime dependency.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..paths import AGENTS_DIR

ROLES_DIR: Path = AGENTS_DIR / "roles"
DEFAULT_INSTRUCTION_VERSION = "unassigned"


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    """Parse a flat YAML file with top-level scalars and one-level lists."""
    out: dict[str, Any] = {}
    current_list: list[str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if current_list is not None and line.lstrip().startswith("- "):
            current_list.append(line.lstrip()[2:].strip())
            continue
        if line.startswith(" ") or line.startswith("-"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                current_list = []
                out[key] = current_list
            else:
                current_list = None
                out[key] = value
    return out


def _load_role_manifest(role: str) -> dict[str, Any]:
    """Load the YAML manifest for a role, or an empty dict if not found."""
    path = ROLES_DIR / f"{role}.yaml"
    if path.is_file():
        return _minimal_yaml_load(path.read_text())
    return {}


def get_instruction_version(role: str) -> str:
    """Return the instruction version declared by a role manifest.

    Falls back to ``DEFAULT_INSTRUCTION_VERSION`` when the manifest does not
    declare one.
    """
    manifest = _load_role_manifest(role)
    value = manifest.get("instruction_version")
    if isinstance(value, str) and value:
        return value
    return DEFAULT_INSTRUCTION_VERSION


def get_code_revision(cwd: str | Path | None = None) -> str:
    """Return the current git revision of the repository, or ``'unknown'``."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def role_can(role: str, action: str) -> bool:
    """Return whether a role manifest allows a named action.

    Fail-closed per AUDIT.md (role manifests runtime-enforced): a missing
    manifest, an empty manifest, or a manifest without a ``tools`` list
    denies every action. A role may opt in to all actions with ``"*"``.
    """
    manifest = _load_role_manifest(role)
    if not manifest:
        return False
    allowed = manifest.get("tools", [])
    if not allowed:
        return False
    if "*" in allowed:
        return True
    return action in allowed


def require_role(role: str, action: str) -> None:
    """Raise PermissionError if ``role`` is not allowed ``action``."""
    if not role_can(role, action):
        raise PermissionError(f"role {role!r} is not permitted to {action}")


__all__ = [
    "DEFAULT_INSTRUCTION_VERSION",
    "ROLES_DIR",
    "get_code_revision",
    "get_instruction_version",
    "require_role",
    "role_can",
]
