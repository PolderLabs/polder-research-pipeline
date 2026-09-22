"""Tests for research.config.yaml — the authoritative pipeline configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_research_config_yaml_exists():
    path = _REPO_ROOT / "knowledge-base" / "research.config.yaml"
    assert path.is_file()


def test_research_config_yaml_parses():
    path = _REPO_ROOT / "knowledge-base" / "research.config.yaml"
    with open(path) as f:
        config = yaml.safe_load(f)
    assert config["schema_version"] == 1
    assert "pipeline_version" in config


def test_research_config_enums_aligned_with_paths():
    """P1 exit criterion: no important vocabulary is hard-coded twice."""
    import sys

    sys.path.insert(0, str(_REPO_ROOT / "src"))
    from polder_research.paths import (
        INTAKE_VALID_KIND,
        INTAKE_VALID_STATUS,
        VALID_STATUS,
        VALID_TYPE,
    )

    with open(_REPO_ROOT / "knowledge-base" / "research.config.yaml") as f:
        config = yaml.safe_load(f)

    fm = config["frontmatter"]
    assert set(fm["valid_types"]) == set(VALID_TYPE)
    assert set(fm["valid_status_values"]) == set(VALID_STATUS)

    intake = config["intake"]
    assert set(intake["valid_status"]) == set(INTAKE_VALID_STATUS)
    assert set(intake["valid_kind"]) == set(INTAKE_VALID_KIND)


def test_research_config_task_enum_alignment():
    with open(_REPO_ROOT / "knowledge-base" / "research.config.yaml") as f:
        config = yaml.safe_load(f)
    task = config["task"]
    assert "pending" in task["valid_status"]
    assert "in_progress" in task["valid_status"]
    assert "completed" in task["valid_status"]
    assert "failed" in task["valid_status"]
    assert "blocked" in task["valid_status"]
    assert "abandoned" in task["valid_status"]


def test_research_config_claim_enum():
    with open(_REPO_ROOT / "knowledge-base" / "research.config.yaml") as f:
        config = yaml.safe_load(f)
    claim = config["claim"]
    assert "draft" in claim["valid_status"]
    assert "verified" in claim["valid_status"]
    assert "disputed" in claim["valid_status"]
    assert "superseded" in claim["valid_status"]


def test_research_config_freshness_policy():
    with open(_REPO_ROOT / "knowledge-base" / "research.config.yaml") as f:
        config = yaml.safe_load(f)
    fresh = config["freshness"]
    volatilities = {p["volatility"] for p in fresh["defaults"]}
    for v in ("very-short", "short", "moderate", "long", "stable"):
        assert v in volatilities
