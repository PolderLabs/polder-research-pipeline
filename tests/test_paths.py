"""Tests for polder_research.paths — the single registry of paths and vocabulary."""

from __future__ import annotations

from pathlib import Path

from polder_research.paths import (
    AGENTS_DIR,
    DOMAIN_TYPE,
    DURABLE_EXCLUDE,
    INTAKE_MANIFEST,
    INTAKE_RAW_DIR,
    INTAKE_VALID_KIND,
    INTAKE_VALID_STATUS,
    NO_ORPHAN_CHECK,
    REPO_ROOT,
    REQUIRED_FM_KEYS,
    RESEARCH_DIR,
    RESEARCH_EVENTS_DIR,
    RESEARCH_GENERATED_DIR,
    RESEARCH_HANDOFFS_DIR,
    RESEARCH_HEALTH,
    RESEARCH_LOCKS_DIR,
    RESEARCH_MAINTENANCE_DIR,
    RESEARCH_RUNS_DIR,
    RESEARCH_STATE,
    RESEARCH_TASKS_DIR,
    SCHEMAS_DIR,
    SKIP_PARTS,
    TEMPLATES_DIR,
    VALID_STATUS,
    VALID_TYPE,
    VAULT_DIRS,
)


def test_repo_root_is_absolute_path():
    assert isinstance(REPO_ROOT, Path)
    assert (REPO_ROOT / "AGENTS.md").is_file()
    assert (REPO_ROOT / "knowledge-base" / "AUDIT.md").is_file()


def test_vault_dirs_canonical():
    expected = (
        "knowledge-base/00-home",
        "knowledge-base/01-project",
        "knowledge-base/02-research",
        "knowledge-base/03-system",
        "knowledge-base/04-decisions",
        "knowledge-base/05-operations",
        "knowledge-base/06-sources",
        "knowledge-base/90-inbox",
        "knowledge-base/99-templates",
    )
    assert VAULT_DIRS == expected


def test_required_frontmatter_keys():
    assert "type" in REQUIRED_FM_KEYS
    assert "status" in REQUIRED_FM_KEYS
    assert "tags" in REQUIRED_FM_KEYS


def test_valid_type_contains_all_audit_values():
    # §3 of the audit defines these frontmatter types
    for t in (
        "index",
        "moc",
        "guide",
        "template",
        "inbox",
        "project",
        "research",
        "system",
        "decision",
        "operation",
        "experiment",
        "source",
    ):
        assert t in VALID_TYPE


def test_valid_status_values():
    for s in ("current", "draft", "stale", "superseded"):
        assert s in VALID_STATUS


def test_domain_type_mapping():
    assert DOMAIN_TYPE["knowledge-base/00-home"] == "guide"
    assert DOMAIN_TYPE["knowledge-base/01-project"] == "project"
    assert DOMAIN_TYPE["knowledge-base/90-inbox"] == "inbox"


def test_skip_parts_includes_control_plane():
    # §3.16: all tools must use one scan scope
    assert ".research" in SKIP_PARTS
    assert "schemas" in SKIP_PARTS
    assert "agents" in SKIP_PARTS
    assert "src" in SKIP_PARTS
    assert "tests" in SKIP_PARTS


def test_ensure_research_dirs_idempotent(tmp_path: Path, monkeypatch):
    """ensure_research_dirs() creates the directory tree under REPO_ROOT."""
    from polder_research import paths as paths_mod

    # Patch REPO_ROOT so paths computed from it reflect the temp directory
    monkeypatch.setattr(paths_mod, "REPO_ROOT", tmp_path)
    # Patch the RESEARCH_* constants directly — they were bound at import time
    fake = tmp_path / ".research"
    for k, v in {
        "RESEARCH_DIR": fake,
        "RESEARCH_EVENTS_DIR": fake / "events",
        "RESEARCH_TASKS_DIR": fake / "tasks",
        "RESEARCH_RUNS_DIR": fake / "runs",
        "RESEARCH_HANDOFFS_DIR": fake / "handoffs",
        "RESEARCH_MAINTENANCE_DIR": fake / "maintenance",
        "RESEARCH_LOCKS_DIR": fake / "locks",
        "RESEARCH_GENERATED_DIR": fake / "generated",
    }.items():
        monkeypatch.setattr(paths_mod, k, v, raising=False)
    paths_mod.ensure_research_dirs()
    for sub in ("events", "tasks", "runs", "handoffs", "maintenance", "locks", "generated"):
        assert (fake / sub).is_dir(), f"{sub} not created"
    # idempotent
    paths_mod.ensure_research_dirs()
    assert (fake / "events").is_dir()


def test_intake_status_vocabulary():
    assert "new" in INTAKE_VALID_STATUS
    assert "filed" in INTAKE_VALID_STATUS
    assert "rejected" in INTAKE_VALID_STATUS


def test_intake_kind_vocabulary_includes_canonical():
    # §3.4 source_type values are accepted via intake
    assert "paper" in INTAKE_VALID_KIND
    assert "dataset" in INTAKE_VALID_KIND
    assert "documentation" in INTAKE_VALID_KIND


def test_research_dirs_are_under_research_dir():
    assert RESEARCH_EVENTS_DIR.parent == RESEARCH_DIR
    assert RESEARCH_TASKS_DIR.parent == RESEARCH_DIR
    assert RESEARCH_RUNS_DIR.parent == RESEARCH_DIR
    assert RESEARCH_HANDOFFS_DIR.parent == RESEARCH_DIR
    assert RESEARCH_MAINTENANCE_DIR.parent == RESEARCH_DIR
    assert RESEARCH_LOCKS_DIR.parent == RESEARCH_DIR
    assert RESEARCH_GENERATED_DIR.parent == RESEARCH_DIR


def test_state_and_health_paths():
    assert RESEARCH_STATE == RESEARCH_DIR / "state.json"
    assert RESEARCH_HEALTH == RESEARCH_DIR / "health.json"


def test_durable_exclude_set_is_frozenset():
    assert isinstance(DURABLE_EXCLUDE, frozenset)
    assert "README.md" in DURABLE_EXCLUDE
    assert "AGENTS.md" in DURABLE_EXCLUDE


def test_no_orphan_check_set_is_frozenset():
    assert isinstance(NO_ORPHAN_CHECK, frozenset)
    assert "knowledge-base/90-inbox" in NO_ORPHAN_CHECK
    assert "knowledge-base/99-templates" in NO_ORPHAN_CHECK


def test_canonical_paths_exist():
    assert SCHEMAS_DIR.is_dir()
    assert AGENTS_DIR.is_dir()
