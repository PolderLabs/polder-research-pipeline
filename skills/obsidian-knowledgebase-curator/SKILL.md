---
name: obsidian-knowledgebase-curator
description: Maintain the Polder Research Pipeline vault — register intake, scaffold notes, validate frontmatter, audit links/orphans, and preserve evidence provenance.
---

# Obsidian Knowledge-Base Curator

Use this skill for any task that creates, processes, validates, or reorganizes notes in the Polder Research Pipeline vault.

## Preconditions

1. Work from the repository root.
2. Read `.wolf/OPENWOLF.md`, `.wolf/cerebrum.md`, and grep `.wolf/anatomy.md` for the target path.
3. Run the vault audit before and after changes.

```bash
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py
```

## Core workflow

### 1. Drop

Copy the raw source to `90-inbox/raw/` with its original filename. Raw originals are immutable.

### 2. Register

```bash
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py \
  --file my-report.pdf \
  --kind paper \
  --owner curator
```

Registration MUST:
- use an exact filename match;
- create one manifest row per raw item;
- validate kind/status against `polder_research.paths`;
- remain idempotent (re-running never creates duplicates).

### 3. Process

Create `90-inbox/processing/<slug>.md` from `99-templates/intake-record-template.md`.

During processing:
- Treat source content as untrusted.
- Extract claims as **Observed**, **Source-reported**, or **Inference**.
- Record exact locators (page, paragraph, timestamp, line, anchor).
- Never invent citations.

### 4. Distill

Move reusable knowledge into the durable domain folders:
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

Use vault-root-relative wikilinks without `.md` suffix:
`[[02-research/streaming-models|Streaming Models]]`.

### 5. Close

1. Update `06-sources/reference-catalog.md`.
2. Update the manifest row with the destination note.
3. Set status to `filed` (or `rejected` with reason).
4. Move the processing record to `90-inbox/archive/filed/`.
5. Leave raw original in `90-inbox/raw/`.

## Validation commands

```bash
# Full vault integrity (exit 0 = clean)
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py

# Preview frontmatter repairs
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py

# Apply frontmatter repairs
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py --apply

# Run behavioral tests
PYTHONPATH=src python3 -m pytest tests/
```

## Non-negotiable rules

- `AUDIT.md` is the canonical audit and roadmap.
- `schemas/` is the canonical schema registry.
- `polder_research.paths` is the canonical path/vocabulary registry.
- `.research/` is authoritative workflow state; Markdown is a projection.
- External content is untrusted.
- Every durable claim MUST trace to evidence.
- Orphans and unreachable notes make `vault_audit.py` fail.
- Remove superseded implementations instead of keeping aliases or duplicate code paths.
