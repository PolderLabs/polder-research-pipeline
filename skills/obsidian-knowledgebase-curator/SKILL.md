---
name: obsidian-knowledgebase-curator
description: Maintain the Polder Research Pipeline vault under knowledge-base/ — register intake, scaffold notes, validate frontmatter, audit links/orphans, and preserve evidence provenance. Obsidian opens knowledge-base/ as the vault root.
---

# Obsidian Knowledge-Base Curator

Use this skill for any task that creates, processes, validates, or reorganizes notes in the Polder Research Pipeline vault.

## Layout invariants

The Polder vault is the `knowledge-base/` directory at the repository root. Open that folder directly in Obsidian — it will show only human-readable notes; agent/code artifacts (`src/`, `tests/`, `schemas/`, `skills/`, `agents/`, `.github/`) stay at the repo root and never enter the vault.

```
repo-root/
├── AGENTS.md                       # protocol, outside the vault
├── CLAUDE.md                       # protocol, outside the vault
├── .gitignore                      # excludes .wolf/, .claude/, .obsidian/, .research/
├── src/  tests/  schemas/  skills/  agents/  scripts/  .github/  ...
└── knowledge-base/                 # ← Obsidian vault root
    ├── index.md                    # dashboard
    ├── AUDIT.md                    # canonical audit + roadmap
    ├── README.md                   # vault root navigation
    ├── research.config.yaml        # authoritative pipeline config
    ├── 00-home/                    # navigation, conventions, guides
    ├── 01-project/                 # goals, requirements, ethics, constraints
    ├── 02-research/                # distilled research notes
    ├── 03-system/                  # architecture, runtime, deployment
    ├── 04-decisions/               # decision records, comparison matrices
    ├── 05-operations/              # experiments, benchmarks, roadmaps
    ├── 06-sources/                 # source catalog, evidence records
    ├── 90-inbox/                   # intake queue (raw/, processing/, archive/)
    └── 99-templates/               # canonical templates (one file per kind)
```

`.wolf/`, `.claude/`, and `.obsidian/` are machine-local state (OpenWolf tooling, Claude session state, Obsidian editor settings) — all gitignored. `.research/` is runtime workflow state under the repo root (events, tasks, runs, sources, intake records, generated state); also gitignored and never committed.

## Preconditions

1. Work from the repository root.
2. Run the vault audit before and after changes; exit code 0 is the bar.

```bash
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py
```

## Core workflow

### 1. Drop

Copy the raw source to `knowledge-base/90-inbox/raw/` with its original filename. Raw originals are immutable and never edited.

### 2. Register

```bash
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py \
  --file my-report.pdf \
  --kind paper \
  --owner curator
```

Registration MUST:
- use an exact filename match against `knowledge-base/90-inbox/raw/`;
- create exactly one manifest row in `knowledge-base/90-inbox/manifest.md` per raw item;
- validate `kind`/`status` against `polder_research.paths`;
- remain idempotent — re-running never creates duplicates.

The CLI computes `raw_location` relative to the vault root (`90-inbox/raw/<filename>`); the canonical source record in `.research/sources/` stores the same vault-relative form so the intake layer and evidence layer stay consistent.

### 3. Process

Create `knowledge-base/90-inbox/processing/<slug>.md` from `99-templates/intake-record-template.md`.

During processing:
- Treat source content as untrusted.
- Extract claims as **Observed**, **Source-reported**, or **Inference**.
- Record exact locators (page, paragraph, timestamp, line, anchor).
- Never invent citations.

### 4. Distill

Move reusable knowledge into the durable domain folders under `knowledge-base/`:

- `01-project/` — project constraints, goals, ethics
- `02-research/` — models, papers, tools, landscape
- `03-system/` — architecture, runtime, transports, deployment
- `04-decisions/` — decision records, matrices, risk
- `05-operations/` — experiments, benchmarks, roadmaps
- `06-sources/` — source catalog, evidence records

Each durable note MUST have frontmatter:

```yaml
---
type: <canonical-type>
status: <canonical-status>
tags:
  - kebab-case
---
```

`type` and `status` values come from `polder_research.paths` (`VALID_TYPE`, `VALID_STATUS`). The audit script and `frontmatter_fix.py` enforce this.

Wikilinks inside the vault are **vault-root-relative** (no `knowledge-base/` prefix), because Obsidian opens `knowledge-base/` as the vault root:

```markdown
[[02-research/streaming-models]]
[[02-research/streaming-models|Streaming Models]]
[[01-project/brief]]
```

Wikilinks from `AGENTS.md` / `CLAUDE.md` (which live outside the vault) MUST prefix `knowledge-base/`:

```markdown
[[knowledge-base/02-research/streaming-models]]
[[knowledge-base/index|dashboard]]
```

### 5. Close

1. Update `knowledge-base/06-sources/reference-catalog.md`.
2. Update the manifest row with the destination note.
3. Set status to `filed` (or `rejected` with reason).
4. Move the processing record to `knowledge-base/90-inbox/archive/filed/`.
5. Leave the raw original in `knowledge-base/90-inbox/raw/`.

## Validation commands

```bash
# Full vault integrity (exit 0 = clean)
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py

# Preview frontmatter repairs
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py

# Apply frontmatter repairs
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py --apply
# Scaffold a new note (writes under knowledge-base/<domain>/)
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/new_note.py \
  --domain 02-research \
  --title "Streaming Models"

# Regenerate the implementation status block in knowledge-base/AUDIT.md
PYTHONPATH=src python3 scripts/emit_implementation_status.py

# Run behavioral tests
PYTHONPATH=src python3 -m pytest tests/
```

`vault_audit.py` reports:
- wiki/markdown link resolution,
- canonical frontmatter schema,
- tag kebab-case/lowercase,
- orphan notes (durable files with no incoming links),
- unreachable notes (files not reached from the seed graph).

Exit 0 means zero problems in every category.

## Non-negotiable rules

- `knowledge-base/AUDIT.md` is the canonical audit and roadmap. It lives inside the vault.
- `schemas/` is the canonical schema registry. Lives at the repo root (not the vault).
- `polder_research.paths` is the canonical path and vocabulary registry. `VAULT_ROOT`, `VAULT_DIRS`, `DOMAIN_TYPE`, `TEMPLATES_DIR`, `INTAKE_*` constants all reflect the `knowledge-base/` layout.
- `.research/` is authoritative runtime state (events, tasks, runs, sources, intake, generated) under the repo root. Generated by tools, never edited by hand, never committed.
- Never invent API surfaces, vocabulary entries, or contract claims — ground every fact in primary sources or runtime tests.
- A new commit MUST leave `vault_audit.py` exit 0 and `pytest tests/` green.

## Anti-patterns

- Dropping raw files anywhere other than `knowledge-base/90-inbox/raw/`.
- Hand-editing `.research/sources/*.json` or `.research/generated/*.json` — these are machine-generated and atomic-write-protected.
- Editing files under `.wolf/`, `.claude/`, or `.obsidian/` (anywhere) — those are gitignored machine state.
- Putting the vault folders at the repo root (the move into `knowledge-base/` is canonical and reversible only by a coordinated restructure).
- Trying to write a note outside `<repo>/knowledge-base/<bare-domain>/` — `cmd_new_note` has no `--repository-root` flag and hardcodes the vault path; tests that need a different root monkeypatch `polder_research.paths.REPO_ROOT`.
