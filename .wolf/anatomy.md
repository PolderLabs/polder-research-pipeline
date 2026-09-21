# OpenWolf Anatomy

Quick navigation by file. Grep `.wolf/anatomy.md` for the path BEFORE reading it.

## Repository root

| Path | Purpose |
|---|---|
| `AUDIT.md` | Canonical audit, priority roadmap, source of truth |
| `README.md` | Top-level landing page |
| `AGENTS.md` | Agent protocol contract |
| `index.md` | Obsidian dashboard |
| `research.config.yaml` | Pipeline configuration (enums, defaults) |

## Control plane (authoritative)

| Path | Purpose |
|---|---|
| `schemas/` | JSON Schemas for all structured records |
| `agents/` | Agent contracts (common.md + role docs) |
| `agents/roles/` | Per-role YAML manifests |
| `src/polder_research/` | Python package (paths, events, tasks, runs, handoffs, evidence, scripts) |
| `tests/` | pytest suite |
| `.research/` | Runtime control-plane state (events, tasks, runs, handoffs, sources, claims) |

## Skill infrastructure

| Path | Purpose |
|---|---|
| `skills/obsidian-knowledgebase-curator/SKILL.md` | Skill contract |
| `skills/obsidian-knowledgebase-curator/README.md` | Skill overview |
| `skills/obsidian-knowledgebase-curator/scripts/` | Validator and intake scripts |

## Content plane (human projection)

| Path | Purpose |
|---|---|
| `00-home/` | Operating guides, navigation, glossary, evidence model |
| `01-project/` | Project brief, goals |
| `02-research/` | Distilled research |
| `03-system/` | System architecture notes |
| `04-decisions/` | Decision records |
| `05-operations/` | Operations notes |
| `06-sources/` | Source catalog (`reference-catalog.md` is canonical here) |
| `90-inbox/` | Inbox queue and processing records |
| `99-templates/` | Note templates |

## Key references

- `AUDIT.md` §3, §5 — repository structure rules
- `00-home/naming-conventions.md` — naming rules
- `00-home/glossary.md` — canonical terminology
- `00-home/evidence-model.md` — evidence graph
- `00-home/provenance-model.md` — provenance trace
- `01-project/brief.md` — project mission and scope
- `06-sources/reference-catalog.md` — citation catalog
- `99-templates/intake-record-template.md` — intake processing record structure
