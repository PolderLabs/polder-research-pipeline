---
type: moc
status: current
tags:
  - navigation
  - home
---

# Home

Welcome to the Polder Research Pipeline knowledge base. Start here.

## Entry points

- [[index|Dashboard]] — live vault stats, domain coverage, inbox status, health metrics.
- [[vault-standards|Vault standards]] — frontmatter schema, wikilink rules, orphan definition.
- [[knowledge-base-guide|Knowledge base guide]] — folder contracts, note lifecycle, cross-linking.
- [[research-intake-guide|Research intake guide]] — the 6-step raw-to-note pipeline.
- [[research-methods|Research methods]] — protocol-first systematic review controls, evidence appraisal, and reproducibility limits.
- [[03-system/classification-providers|Classification providers]] — categories, tags, dimensions, routing, and Jev/Laya setup.
- [[03-system/classification-operations|Classification operations]] — privacy, human review, evaluation, and staged automation policy.

## Vault overview

The repository root is the Obsidian vault. Six numbered domains hold durable notes; raw material drops into the intake queue.

| Domain | What lives here |
|---|---|
| [[01-project/README|01-project]] | Goals, requirements, ethics, constraints |
| [[02-research/README|02-research]] | Distilled research: models, papers, tools |
| [[03-system/README|03-system]] | Architecture, performance, deployment |
| [[04-decisions/README|04-decisions]] | Decision records, comparison matrices |
| [[05-operations/README|05-operations]] | Experiments, benchmarks, roadmaps |
| [[06-sources/README|06-sources]] | Source catalog and evidence records |
| [[90-inbox/README|90-inbox]] | Raw drops and intake queue |

## Quick commands

```bash
# Full vault audit
python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py

# Register a new raw item
python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py \
  --file my-paper.pdf --kind pdf --owner curator

# Scaffold a new note
python3 skills/obsidian-knowledgebase-curator/scripts/new_note.py \
  --domain 02-research --title "Streaming Autoregressive Models" --tags ai,streaming

# Auto-fix frontmatter gaps
python3 skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py --apply
```
