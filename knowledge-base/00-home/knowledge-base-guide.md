---
type: guide
status: current
tags:
  - knowledge-base
  - guide
---

# Knowledge Base Guide

This vault is the repository. The repository is the vault. All documentation lives here.

## Folder contracts

### `01-project` — Goals and Constraints

Everything that defines what the project is, why it exists, and what it cannot do.

- **Goals and vision**: what success looks like.
- **Requirements**: functional and non-functional requirements.
- **Ethics and safety**: constraints that must never be violated.

### `02-research` — Distilled Research

Distilled knowledge from papers, models, tools, and the technology landscape. Notes here represent the curator's synthesis, not raw source text.

- **Models and Backends**: papers, model cards, integration candidates.
- **Perception and Control**: segmentation, tracking, pose estimation, matting.
- **Streaming and Latency**: autoregressive models, causal architectures, latency tradeoffs.
- **Generative Approaches**: diffusion, GAN, hybrid generative models.

### `03-system` — Architecture and Runtime

How the system is built and how it runs.

- **Architecture**: component diagrams, data flows, interfaces.
- **Runtime and Transports**: IPC, network protocols, data formats.
- **Performance and Latency**: benchmarks, SLAs, bottlenecks.
- **Deployment**: environments, configuration, rollouts.

### `04-decisions` — Decision Records

Every significant decision, with rationale and alternatives considered.

- **Accepted Decisions**: closed decisions, with consequences tracked.
- **Pending Decisions**: open questions awaiting resolution.
- **Decision Records**: per-decision notes with ADRC format.

### `05-operations` — Experiments and Roadmaps

Operational knowledge: what was tried, what worked, what comes next.

- **Experiments**: experiment definitions, protocols, results.
- **Benchmarks**: reproducible benchmark definitions and schemas.
- **Roadmaps**: milestone plans, priorities.

### `06-sources` — Source Catalog

Canonical bibliography and evidence records.

- **Papers**: academic references with citation metadata.
- **Repositories**: code repositories, model weights sources.
- **Documentation**: official docs, standards.
- **Evidence Records**: structured evidence from intake processing.

### `90-inbox` — Intake Queue

Raw drops and the processing pipeline. See [[00-home/research-intake-guide|Research intake guide]].

### `99-templates` — Note Templates

Canonical templates for each note type. Copy from here; never create parallel templates.

## Note lifecycle

1. **Idea** — enters the vault as a `draft` note.
2. **Draft** — actively being developed; status remains `draft`.
3. **Current** — stable, reviewed, accepted. Status becomes `current`.
4. **Stale** — not updated in 90+ days; needs review.
5. **Superseded** — replaced by another note; retains history.

## Cross-linking

Every note should be reachable from at least one other note. Orphan notes are surfaced on the dashboard and should be linked or retired.

Use wikilinks: `[[path]]` or `[[path|alias]]`. Vault-root-relative, no `.md`.

## Tag taxonomy and automatic classification

The versioned category and tag vocabulary in `research.config.yaml` drives
automatic classification of sources, claims, entities, and segments. Change
the taxonomy there and increment its version. Human tags are preserved. Low
confidence results remain review-required; tagging never establishes evidence
or replaces systematic review screening, appraisal, extraction, or adjudication.
Keep manually added tags:
- Lowercase, kebab-case.
- One concept per tag.
- Meaningful: `ai-inference`, `streaming`, `latency`.

## Adding a new note

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/new_note.py \
  --domain 02-research \
  --title "My New Topic" \
  --tags ai,streaming
```

Or copy a template from `99-templates/` and fill it in.

## Related

- [[00-home/vault-standards|Vault standards]]
- [[00-home/research-intake-guide|Research intake guide]]
- [[AGENTS|AGENTS.md]] — full agent protocol
