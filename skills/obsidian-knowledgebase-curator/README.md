# obsidian-knowledgebase-curator

Maintain the Polder Research Pipeline's knowledge-base vault: validate frontmatter, fix missing fields, audit links/orphans, register intake items, scaffold new notes.

## Quick start

```bash
# Run from the repository root.
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py --apply
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py --file my-report.pdf --kind paper
PYTHONPATH=src python3 skills/obsidian-knowledgebase-curator/scripts/new_note.py --domain 02-research --title "My Topic"
```

## What this skill does

1. **`vault_audit.py`** — Validates every vault note:
   - Required frontmatter (type, status, tags)
   - Tag syntax (kebab-case ASCII only)
   - Required vault folders present
   - Wikilink resolution (no broken `[[...]]` links)
   - Markdown link resolution (no broken `[...](...)`)
   - Orphan detection (durable notes with no inlinks)
   - Reachability (every note reachable from a seed: index.md, README.md, AUDIT.md, AGENTS.md, CLAUDE.md, or top-level domain notes)

2. **`frontmatter_fix.py`** — Auto-adds missing frontmatter:
   - Inferred `type` from domain (00-home→guide, 01-project→project, 02-research→research, 04-decisions→decision, etc.)
   - `status: draft` placeholder
   - Single `tags:` entry (`knowledge-base` by default)

3. **`intake_register.py`** — Records raw material in `90-inbox/manifest.md`:
   - Validates `kind` against canonical source_type vocabulary
   - Validates `status` against intake lifecycle states
   - Inserts row in correct order (header → separator → newest-first data row)

4. **`new_note.py`** — Scaffolds a new durable note:
   - Wraps `99-templates/<type>-template.md` (or generic template if missing)
   - Writes to the requested domain folder
   - Validates frontmatter against `polder_research.paths.REQUIRED_FM_KEYS`

## Source of truth

- All vocabulary, paths, and enums come from `polder_research.paths` (single registry)
- All schemas come from `schemas/` (root, loaded by `polder_research.schemas`)
- Audit policy is centralized; do not duplicate the link/frontmatter/taxonomy rules
