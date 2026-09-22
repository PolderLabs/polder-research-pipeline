"""Shared pytest fixtures for the polder-research-pipeline tests.

The vault layout (per AUDIT.md §3 and the rearrangement that moved
research notes into ``knowledge-base/``) is reflected here:
- ``00-home``–``99-templates`` domain folders live under
  ``knowledge-base/``;
- root-level durable pages are ``AGENTS.md``, ``CLAUDE.md``;
- ``knowledge-base/index.md``, ``knowledge-base/README.md``,
  ``knowledge-base/AUDIT.md`` are the in-vault durable pages.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOMAINS = (
    "00-home",
    "01-project",
    "02-research",
    "03-system",
    "04-decisions",
    "05-operations",
    "06-sources",
    "90-inbox",
    "99-templates",
)


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a minimal vault skeleton in a temp directory.

    Layout:
        <tmp_path>/knowledge-base/{00-home..99-templates}
        <tmp_path>/knowledge-base/index.md
        <tmp_path>/knowledge-base/README.md
        <tmp_path>/knowledge-base/AUDIT.md
        <tmp_path>/AGENTS.md
        <tmp_path>/CLAUDE.md
    """
    vault = tmp_path / "knowledge-base"
    for d in DOMAINS:
        (vault / d).mkdir(parents=True, exist_ok=True)
    (vault / "90-inbox" / "raw").mkdir(parents=True, exist_ok=True)
    (vault / "90-inbox" / "processing").mkdir(parents=True, exist_ok=True)
    (vault / "90-inbox" / "archive" / "filed").mkdir(parents=True, exist_ok=True)
    (vault / "90-inbox" / "archive" / "rejected").mkdir(parents=True, exist_ok=True)

    (vault / "index.md").write_text(
        "---\ntype: moc\nstatus: current\ntags:\n  - dashboard\n---\n\n# Dashboard\n",
        encoding="utf-8",
    )
    (vault / "README.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - navigation\n---\n\n# Root\n",
        encoding="utf-8",
    )
    (vault / "AUDIT.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - audit\n---\n\n# Audit\n",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - agents\n---\n\n# Agents\n",
        encoding="utf-8",
    )
    (tmp_path / "CLAUDE.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - agents\n---\n\n# Claude\n",
        encoding="utf-8",
    )

    (vault / "00-home" / "README.md").write_text(
        "---\ntype: moc\nstatus: current\ntags:\n  - home\n---\n\n# Home\n\n[[knowledge-base/index|Dashboard]]\n",
        encoding="utf-8",
    )
    (vault / "90-inbox" / "README.md").write_text(
        "---\ntype: inbox\nstatus: current\ntags:\n  - intake\n---\n\n# Inbox\n",
        encoding="utf-8",
    )
    (vault / "90-inbox" / "manifest.md").write_text(
        "---\ntype: inbox\nstatus: current\ntags:\n  - manifest\n---\n\n"
        "# Manifest\n\n## Queue\n\n"
        "| Item | Kind | Added | Status | Owner | Outcome |\n"
        "|---|---|---|---|---|---|\n",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def repo_root() -> Path:
    """The real repository root — templates resolve against knowledge-base/."""
    return Path(__file__).resolve().parents[1]
