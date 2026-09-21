"""Tests for the agents/ directory — role docs and role manifests exist and are valid."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


_REPO_ROOT = Path(__file__).resolve().parents[1]


AGENTS_DIR = _REPO_ROOT / "agents"
ROLES_DIR = AGENTS_DIR / "roles"


EXPECTED_ROLES = {
    "orchestrator",
    "research-agent",
    "acquisition-agent",
    "pipeline-processing-agent",
    "classification-agent",
    "verification-agent",
    "sorting-cleanup-agent",
    "knowledge-maintenance-agent",
    "knowledge-query-agent",
    "synthesis-agent",
    "evolution-agent",
}


def test_common_contract_exists():
    assert (AGENTS_DIR / "common.md").is_file()


def test_all_role_docs_exist():
    for role in EXPECTED_ROLES:
        path = AGENTS_DIR / f"{role}.md"
        assert path.is_file(), f"missing agent doc: {path}"


def test_all_role_manifests_exist():
    for role in EXPECTED_ROLES:
        path = ROLES_DIR / f"{role}.yaml"
        assert path.is_file(), f"missing role manifest: {path}"


def test_role_manifests_parse_as_yaml():
    for role in EXPECTED_ROLES:
        path = ROLES_DIR / f"{role}.yaml"
        manifest = yaml.safe_load(path.read_text())
        assert manifest["schema_version"] == 1
        assert manifest["role"] == role
        assert "read" in manifest
        assert "write" in manifest
        assert "forbidden" in manifest


def test_role_manifests_forbid_schemas():
    # evolution-agent is the one role allowed to propose schema changes,
    # so we exclude it from this check (the agent role doc + audit §44 cover
    # the gating protocol: migrations require review before apply).
    for role in EXPECTED_ROLES:
        if role == "evolution-agent":
            continue
        path = ROLES_DIR / f"{role}.yaml"
        manifest = yaml.safe_load(path.read_text())
        assert "schemas/**" in manifest["forbidden"], (
            f"role {role} must forbid writing to schemas/**"
        )


def test_common_contract_frontmatter():
    text = (AGENTS_DIR / "common.md").read_text()
    assert text.startswith("---\n")
    assert "type: guide" in text
    assert "tags:" in text
