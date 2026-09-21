---
type: index
status: current
tags:
  - navigation
---

# Polder Research Pipeline

Self-evolving knowledge base for realtime AI-driven visual platform research. The repository root **is** the Obsidian vault.

## Quick start

1. Open this folder in Obsidian (vault root = repo root).
2. Enable **Dataview** and **CSS snippets → polder-dashboard** in settings.
3. Start at [[index|the dashboard]].

## What's here

| Folder | Purpose |
|---|---|
| `00-home` | Navigation hub and operating guides. |
| `01-project` | Goals, requirements, ethics, stable constraints. |
| `02-research` | Distilled research: models, papers, tools, technology landscape. |
| `03-system` | Architecture, performance, transports, deployment, runtime. |
| `04-decisions` | Decision records, comparison matrices, risk assessments. |
| `05-operations` | Experiments, benchmarks, roadmaps. |
| `06-sources` | Source catalog and evidence records. |
| `90-inbox` | Raw drops and the intake queue. |
| `99-templates` | Canonical note templates. |
| `skills/obsidian-knowledgebase-curator/scripts/` | Validator and helper scripts. |

## Validators

Run from the repo root:

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py   # full audit, exit 0 = clean
python3 skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py --apply
python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py --file <path> --kind pdf --owner curator
python3 skills/obsidian-knowledgebase-curator/scripts/new_note.py --domain 02-research --title "My Topic" --tags ai
```

## License

Private repository. All rights reserved.
