---
type: guide
status: current
topic: agent-protocols
tags:
  - knowledge-base
---

<!-- openwolf:begin -->
# OpenWolf

This project uses OpenWolf for context management. Read and follow `.wolf/OPENWOLF.md` at session start. Check `.wolf/cerebrum.md` before generating code. Grep `.wolf/anatomy.md` for a file's path before reading it (never read the whole index).
<!-- openwolf:end -->

# Agents

**Repository:** Polder Research Pipeline — a self-evolving knowledge base for realtime AI-driven visual platform research.

## Entry point

**Dashboard:** `index.md` — vault stats, domain coverage, inbox status, health, self-evolution metrics.

## Repository structure

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

## Processing raw material

1. **Drop** — copy the raw file to `90-inbox/raw/`. Keep the original filename.
2. **Register** — add a row to `90-inbox/manifest.md`: `python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py --file my-report.pdf --kind pdf --owner curator`
3. **Process** — create a processing note in `90-inbox/processing/<name>.md` from `99-templates/intake-record-template.md`.
4. **Distill** — extract claims, label Observed / Source-reported / Inference, cross-link to domain notes, update `06-sources/reference-catalog.md`.
5. **Close** — record the destination note in the manifest, mark `filed`. Move the processing note to `90-inbox/archive/filed/`. The raw original stays in `90-inbox/raw/`.

Full contract: `skills/obsidian-knowledgebase-curator/SKILL.md`.

## Validators

Run from the repo root:
- `vault_audit.py` — full vault integrity: links, frontmatter, orphans, tags, structure. Exit 0 = clean.
- `frontmatter_fix.py --apply` — auto-fix missing `type`/`status`/`tags`.
- `intake_register.py --file …` — register raw item before processing.
- `new_note.py --domain 02-research --title "My Topic" --tags ai` — scaffold a note.

## Frontmatter schema

Every vault `.md` note needs:
```yaml
type: <value>   # index | moc | guide | template | inbox | project | research | system | decision | operation | experiment | source
status: <value>  # current | draft | stale | superseded
tags:
  - <tag>       # kebab-case, lowercase
```

## Wikilinks

Vault-root-relative, no `.md`: `[[02-research/streaming-models]]`. With alias: `[[02-research/streaming-models|Streaming Models]]`.

## Related

- [[CLAUDE|CLAUDE.md]] — simplified protocol for Claude sessions.
- [[00-home/vault-standards|Vault standards]].
- [[index|dashboard]].
