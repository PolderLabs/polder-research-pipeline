---
type: guide
status: current
tags:
  - provenance
  - traceability
  - architecture
---

# Provenance Model

How the Polder Research Pipeline tracks where knowledge comes from and who touched it.

## Source-of-truth hierarchy

| Surface | Authority | Rebuildable |
|---|---|---:|
| `research.config.yaml` | Authoritative policy | No |
| `schemas/*.schema.json` | Authoritative contracts | No |
| `agents/roles/*.yaml` | Intended agent capabilities; runtime authorization is not enforced for every boundary | No |
| `.research/sources/*.json` | Authoritative source metadata | No |
| `.research/claims/*.json` | Authoritative structured knowledge | No |
| `.research/entities/*.json` | Authoritative entity identity | No |
| `.research/tasks/*.json` | Authoritative workflow state | No |
| `.research/events/*.json` | Authoritative history | No |
| `.research/protocols/*.json` | Frozen systematic-review methods | No |
| `.research/searches/*.json` | Exact search executions | No |
| `.research/candidates/*.json` | Search hits, including duplicates | No |
| `.research/screenings/*.json` | Independent selection and adjudication decisions | No |
| `.research/extractions/*.json` | Duplicate field extraction and resolution | No |
| `.research/appraisals/*.json` | Instrument-specific study appraisal | No |
| `.research/reports/*.json` | Generated review audit index with record hashes | Yes; regenerate from current records |
| `.research/runs/*.json` | Authoritative run state | No |
| `.research/state.json` | Derived snapshot | Yes |
| `.research/health.json` | Derived health | Yes |
| `00-home/`, `01-project/`, … | Human projection | Yes |

## Event log

Where implemented, state-changing actions emit typed events to `.research/events/`; events are append-only. Event emission is not yet integrated into every research-method writer, so do not rely on the event log alone to reconstruct a systematic review.

Required fields per event:
- `id` (evt_ UUIDv7)
- `event_type`: run.* | task.* | source.* | segment.* | claim.* | entity.* | gap.* | ...
- `actor`: who performed the action
- `role`: which role the actor was operating as
- `timestamp`: ISO 8601 UTC
- `instruction_version`, `config_version`, `code_revision`
- `run_id`, `task_id`
- `action`, `inputs`, `targets`
- `summary`, `result`: ok | warning | error | skipped
- `artifacts[]`
- `error.sanitized_message`, `error.category`

## Claim provenance trace

Every claim in the knowledge base MUST be able to answer:

> "Why do we believe this, from exactly where, under which version/scope?"

The trace: `claim → evidence edge → source segment → source record`.

A claim with `claim_status: verified` MUST have:
- At least one evidence edge with `relation: supports`
- `verification.checks_performed` listing which checks passed
- `verification.verified_at` and `verification.verified_by`

## Source lineage

Sources can relate to each other:
- `cites` — source explicitly references another source
- `mirrors` — source mirrors content from another source
- `republishes` — source republishes content from another source
- `summarizes` — source summarizes another source
- `forks` — source is a fork of another source
- `derives_from` — source derives from another source
- `vendor_claim_about` — source makes claims about another entity
- `independent_replication_of` — source is an independent replication

**Independence**: Do not count derivative reporting as independent evidence. A source that cites a press release about a model is not independent evidence for that model's capabilities.

## Snapshot isolation

Research runs operate on a snapshot of the knowledge base. If a source changes during a run, the run uses the version it started with. Maintenance agents detect and handle post-run source changes.

## Audit trail

The complete audit trail for any claim:
1. Find the claim record (`.research/claims/<id>.json`)
2. For each evidence edge, find the source record
3. For each source, find the raw file and verify `content_sha256`
4. For each event, check `actor`, `role`, `code_revision`, `instruction_version`

For a systematic evidence review, extend the trace backward from the source to its candidate, screening decisions, search execution, and frozen protocol. The generated report indexes these records and hashes their contents. This local record store is not shared durable storage; see [[research-methods|research methods]] for the reproducibility boundary.
