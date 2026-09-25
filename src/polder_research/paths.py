"""Canonical paths and constants for the Polder Research Pipeline.

All other modules should import from here so that the layout is defined once
and the layout never drifts between tools.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[2]


def default_workspace_root() -> Path:
    """Return the checkout root, or the current directory for wheel installs."""
    if (REPO_ROOT / "knowledge-base").is_dir():
        return REPO_ROOT
    return Path.cwd().resolve()


# The Obsidian vault root. Human-readable knowledge lives here so that
# opening ``knowledge-base/`` in Obsidian shows only the curated notes
# (never ``src/``, ``tests/``, ``schemas/``, or other control-plane code).
VAULT_ROOT: Path = REPO_ROOT / "knowledge-base"

# --- canonical domain folders ---------------------------------------------

VAULT_DIRS: tuple[str, ...] = (
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

DOMAIN_TYPE: dict[str, str] = {
    "knowledge-base/00-home": "guide",
    "knowledge-base/01-project": "project",
    "knowledge-base/02-research": "research",
    "knowledge-base/03-system": "system",
    "knowledge-base/04-decisions": "decision",
    "knowledge-base/05-operations": "operation",
    "knowledge-base/06-sources": "source",
    "knowledge-base/90-inbox": "inbox",
    "knowledge-base/99-templates": "template",
}

# Frontmatter vocabulary — single source of truth used by the audit,
# frontmatter fixer, and note scaffolding script.
REQUIRED_FM_KEYS: tuple[str, ...] = ("type", "status", "tags")

VALID_TYPE: frozenset[str] = frozenset(
    {
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
    }
)

VALID_STATUS: frozenset[str] = frozenset({"current", "draft", "stale", "superseded"})

# --- control-plane scan scope (P0 / §3.16) --------------------------------
# All tools must use this registry so that adding a ``SKILL.md`` to a future
# folder cannot accidentally become a target for the frontmatter fixer or
# an orphan in the vault audit.
CONTENT_PLANE_DIRS: frozenset[str] = frozenset(VAULT_DIRS)
CONTROL_PLANE_DIRS: frozenset[str] = frozenset(
    {
        "agents",
        "schemas",
        "src",
        "tests",
        ".research",
        "skills",
        ".githooks",
        ".github",
    }
)

# Folders that are part of the control plane AND skipped by the vault audit.
SKIP_PARTS: frozenset[str] = frozenset(
    {
        ".git",
        ".obsidian",
        ".wolf",
        ".claude",
        ".codex",
        ".research",
        "node_modules",
        ".venv",
        "dist",
        "build",
        "schemas",
        "agents",
        "src",
        "tests",
        ".github",
        ".githooks",
    }
)


# Folders intentionally excluded from the orphan rule. Their contents are
# not part of the durable note graph (inbox, templates).
NO_ORPHAN_CHECK: frozenset[str] = frozenset(
    {"knowledge-base/90-inbox", "knowledge-base/99-templates"}
)

# Root-level files excluded from orphan check — the navigation durable pages.
DURABLE_EXCLUDE: frozenset[str] = frozenset(
    {"AGENTS.md", "CLAUDE.md", "README.md", "knowledge-base/AUDIT.md", "knowledge-base/index.md"}
)

# --- intake manifest --------------------------------------------------------

INTAKE_MANIFEST: Path = VAULT_ROOT / "90-inbox" / "manifest.md"
INTAKE_RAW_DIR: Path = VAULT_ROOT / "90-inbox" / "raw"
INTAKE_PROCESSING_DIR: Path = VAULT_ROOT / "90-inbox" / "processing"
INTAKE_ARCHIVE_FILED: Path = VAULT_ROOT / "90-inbox" / "archive" / "filed"
INTAKE_ARCHIVE_REJECTED: Path = VAULT_ROOT / "90-inbox" / "archive" / "rejected"

INTAKE_VALID_STATUS: frozenset[str] = frozenset(
    {"new", "triaged", "processing", "distilled", "filed", "rejected", "blocked"}
)

# Authoritative intake vocabulary. ``kind`` is a source-kind label that
# mirrors the canonical ``source_type`` set in §3.4 of the audit.
INTAKE_VALID_KIND: frozenset[str] = frozenset(
    {
        # legacy aliases retained for backwards compatibility with the existing
        # intake rows
        "pdf",
        "repository",
        "article",
        "paper",
        "log",
        "transcript",
        "media",
        "url-list",
        "other",
        # canonical source_type values from §3.4
        "documentation",
        "webpage",
        "dataset",
        "benchmark",
        "video",
        "audio",
        "book",
        "standard",
        "issue",
        "discussion",
    }
)

# --- research state --------------------------------------------------------

RESEARCH_DIR: Path = REPO_ROOT / ".research"
RESEARCH_STATE: Path = RESEARCH_DIR / "state.json"
RESEARCH_HEALTH: Path = RESEARCH_DIR / "health.json"
RESEARCH_EVENTS_DIR: Path = RESEARCH_DIR / "events"
RESEARCH_TASKS_DIR: Path = RESEARCH_DIR / "tasks"
RESEARCH_RUNS_DIR: Path = RESEARCH_DIR / "runs"
RESEARCH_HANDOFFS_DIR: Path = RESEARCH_DIR / "handoffs"
RESEARCH_PROTOCOLS_DIR: Path = RESEARCH_DIR / "protocols"
RESEARCH_SEARCHES_DIR: Path = RESEARCH_DIR / "searches"
RESEARCH_CANDIDATES_DIR: Path = RESEARCH_DIR / "candidates"
RESEARCH_SCREENINGS_DIR: Path = RESEARCH_DIR / "screenings"
RESEARCH_APPRAISALS_DIR: Path = RESEARCH_DIR / "appraisals"
RESEARCH_REPORTS_DIR: Path = RESEARCH_DIR / "reports"
RESEARCH_EXTRACTIONS_DIR: Path = RESEARCH_DIR / "extractions"
RESEARCH_INTAKE_DIR: Path = RESEARCH_DIR / "intake"
RESEARCH_MAINTENANCE_DIR: Path = RESEARCH_DIR / "maintenance"
RESEARCH_CLASSIFICATIONS_DIR: Path = RESEARCH_DIR / "classifications"
RESEARCH_LOCKS_DIR: Path = RESEARCH_DIR / "locks"
# Evidence records (authoritative structured state per AUDIT.md §11-14)
EVIDENCE_SOURCES_DIR: Path = RESEARCH_DIR / "sources"
EVIDENCE_CLAIMS_DIR: Path = RESEARCH_DIR / "claims"
EVIDENCE_ENTITIES_DIR: Path = RESEARCH_DIR / "entities"
EVIDENCE_SEGMENTS_DIR: Path = RESEARCH_DIR / "segments"
EVIDENCE_GAPS_DIR: Path = RESEARCH_DIR / "gaps"
EVIDENCE_CONFLICTS_DIR: Path = RESEARCH_DIR / "conflicts"
EVIDENCE_EDGES_DIR: Path = RESEARCH_DIR / "edges"
RESEARCH_GENERATED_DIR: Path = RESEARCH_DIR / "generated"
SCHEMAS_DIR: Path = REPO_ROOT / "schemas"
AGENTS_DIR: Path = REPO_ROOT / "agents"
TEMPLATES_DIR: Path = VAULT_ROOT / "99-templates"


def ensure_research_dirs() -> None:
    """Create the ``.research`` directory tree if it does not exist.

    Idempotent — safe to call from any command. The directories are part of
    the derived state plane and are git-ignored (see §3.12 of the audit).
    """
    for d in (
        RESEARCH_DIR,
        RESEARCH_EVENTS_DIR,
        RESEARCH_TASKS_DIR,
        RESEARCH_RUNS_DIR,
        RESEARCH_HANDOFFS_DIR,
        RESEARCH_PROTOCOLS_DIR,
        RESEARCH_SEARCHES_DIR,
        RESEARCH_CANDIDATES_DIR,
        RESEARCH_SCREENINGS_DIR,
        RESEARCH_APPRAISALS_DIR,
        RESEARCH_REPORTS_DIR,
        RESEARCH_EXTRACTIONS_DIR,
        RESEARCH_INTAKE_DIR,
        RESEARCH_MAINTENANCE_DIR,
        RESEARCH_CLASSIFICATIONS_DIR,
        RESEARCH_LOCKS_DIR,
        RESEARCH_GENERATED_DIR,
        EVIDENCE_SOURCES_DIR,
        EVIDENCE_CLAIMS_DIR,
        EVIDENCE_ENTITIES_DIR,
        EVIDENCE_SEGMENTS_DIR,
        EVIDENCE_GAPS_DIR,
        EVIDENCE_CONFLICTS_DIR,
        EVIDENCE_EDGES_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
