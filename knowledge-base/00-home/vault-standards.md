---
type: guide
status: current
tags:
  - knowledge-base
  - standards
---

# Vault Standards

This document defines the conventions that make the vault self-consistent and agent-readable.

## Frontmatter schema

Every vault `.md` note requires these three fields:

```yaml
type: <value>     # closed vocabulary (see below)
status: <value>   # lifecycle state (see below)
tags:
  - <tag>        # kebab-case, lowercase
```

### `type` closed vocabulary

| Value | When to use |
|---|---|
| `index` | Dashboard (index.md only) |
| `moc` | Domain MOC (domain README.md) |
| `guide` | Operating or onboarding guides |
| `template` | Note templates in `99-templates/` |
| `inbox` | Intake queue items |
| `project` | Goals, requirements, ethics notes |
| `research` | Distilled research notes |
| `system` | Architecture, runtime, deployment notes |
| `decision` | Decision records |
| `operation` | Runbooks, experiments |
| `experiment` | Experiment definitions and results |
| `source` | Source catalog entries |

### `status` closed vocabulary

| Value | Meaning |
|---|---|
| `current` | Active, up-to-date |
| `draft` | Work in progress, not yet stable |
| `stale` | Outdated; needs review or replacement |
| `superseded` | Replaced by another decision or note |

### `tags` rules

- Lowercase, kebab-case: `ai-inference`, `latency`, `streaming`
- One concept per tag; no abbreviations unless universally known
- Tag taxonomy is emergent; no master list required

## Wikilinks

All in-vault references use Obsidian wikilinks:

```
[[00-home/vault-standards|Vault standards]]
[[02-research/streaming-models]]
```

Vault-root-relative paths. No `.md` extension. Optional `|alias`.

## Note naming

- Kebab-case: `streaming-autoregressive-models.md`
- Descriptive, no abbreviations
- One concept per note

## Orphan definition

An **orphan** note is one with zero incoming links from other notes, excluding `index.md`.

```
(p.file.inlinks?.length ?? 0) === 0
```

Orphans are surfaced on the dashboard; they should be cross-linked or retired.

## Dashboard ownership

- `index.md` and `.obsidian/snippets/polder-dashboard.css` are owned by the orchestrating agent.
- Domain `README.md` (MOC) in each numbered folder is owned by its domain owner.
- All other notes are owned by their creating agent.

## Validator contract

`vault_audit.py` is the authoritative integrity check. It runs on every commit via the pre-commit hook. Exit 0 = clean; any non-zero = blocked.

## Related

- [[00-home/knowledge-base-guide|Knowledge base guide]]
- [[00-home/research-intake-guide|Research intake guide]]
