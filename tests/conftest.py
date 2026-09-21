"""pytest configuration — fixtures and path setup for PRP tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a minimal vault skeleton in a temp directory."""
    for d in (
        "00-home", "01-project", "02-research", "03-system",
        "04-decisions", "05-operations", "06-sources",
        "90-inbox/raw", "90-inbox/processing",
        "90-inbox/archive/filed", "90-inbox/archive/rejected",
        "99-templates",
    ):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    (tmp_path / "index.md").write_text(
        "---\ntype: moc\nstatus: current\ntags:\n  - dashboard\n---\n\n# Dashboard\n",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - agents\n---\n\n# Agents\n",
        encoding="utf-8",
    )
    (tmp_path / "AUDIT.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - audit\n---\n\n# Audit\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "---\ntype: guide\nstatus: current\ntags:\n  - navigation\n---\n\n# Root\n",
        encoding="utf-8",
    )

    (tmp_path / "00-home/README.md").write_text(
        "---\ntype: moc\nstatus: current\ntags:\n  - home\n---\n\n# Home\n\n[[index|Dashboard]]\n",
        encoding="utf-8",
    )
    (tmp_path / "90-inbox/README.md").write_text(
        "---\ntype: inbox\nstatus: current\ntags:\n  - intake\n---\n\n# Inbox\n",
        encoding="utf-8",
    )
    (tmp_path / "90-inbox/manifest.md").write_text(
        "---\ntype: inbox\nstatus: current\ntags:\n  - manifest\n---\n\n"
        "# Manifest\n\n## Queue\n\n"
        "| Item | Kind | Added | Status | Owner | Outcome |\n"
        "|---|---|---|---|---|---|\n",
        encoding="utf-8",
    )

    return tmp_path
