---
type: guide
status: current
tags:
  - conventions
  - naming
  - vocabulary
---

# Naming Conventions

Canonical naming rules for the Polder Research Pipeline.

## Note filenames

- **Kebab-case**: lowercase letters, digits, hyphens. No spaces, no underscores.
- **Examples**: `streaming-autoregressive-models.md`, `latency-benchmark-2025.md`
- **Domain prefix not required**: the folder is the domain. Filename is the concept.
- **No `.md` in wikilinks**: `[[streaming-autoregressive-models]]`, not `[[streaming-autoregressive-models.md]]`.

## Wikilinks

- Vault-root-relative: `[[02-research/streaming-models]]`
- With alias: `[[02-research/streaming-models|Streaming Models]]`
- No `.md` suffix in the link target.

## Stable IDs

Structured record IDs use UUIDv7 with a type prefix:

| Prefix | Record type |
|---|---|
| `src_` | source |
| `clm_` | claim |
| `ent_` | entity |
| `seg_` | segment |
| `gap_` | gap |
| `cfl_` | conflict |
| `evt_` | event |
| `tsk_` | task |
| `run_` | run |
| `hnd_` | handoff |
| `dec_` | decision |

UUIDv7 encodes the creation timestamp as the first 48 bits, providing roughly chronological ordering.

## Tags

- **Kebab-case**: `research-pipeline`, `ai`, `streaming`, `benchmark`
- **Lowercase only**
- **No spaces**: use `-` as separator
- **Plural nouns** preferred: `models`, not `model`; `benchmarks`, not `benchmark`
- One tag per concept: `ai` not `artificial-intelligence`

## Frontmatter

| Field | Values |
|---|---|
| `type` | `index`, `moc`, `guide`, `template`, `inbox`, `project`, `research`, `system`, `decision`, `operation`, `experiment`, `source` |
| `status` | `current`, `draft`, `stale`, `superseded` |
| `tags` | kebab-case list |

## Evidence labels

Every claim in a note is labeled:

- **Observed** — measured directly in this research
- **Source-reported** — stated by a source, not verified independently
- **Inference** — derived from other evidence

## Status lifecycle (intake)

`new → triaged → processing → distilled → filed` (or `rejected` at any stage).

## Folder conventions

| Folder | Note type | Notes |
|---|---|---|
| `00-home/` | guide | Vault operating docs |
| `01-project/` | project | Goals, ethics, scope |
| `02-research/` | research | Domain knowledge |
| `03-system/` | system | Technical domain |
| `04-decisions/` | decision | Decision records |
| `05-operations/` | operation | Experiments, runs |
| `06-sources/` | source | Source catalog |
| `90-inbox/` | inbox | Intake queue |
| `99-templates/` | template | Note templates |
