---
type: guide
status: current
tags:
  - agents
  - research
---

# Research Agent

The research agent describes the intended end-to-end role workflow. This repository provides record APIs and provider-backed classification, but does not currently launch specialist agents or execute a brief autonomously. See `knowledge-base/03-system/agent-capabilities.md` before promising an operation.

## Responsibilities

- Execute a run against a brief using its recorded method: `continuous_intelligence` or `systematic_evidence_review`.
- For a systematic review, define eligibility, search, reviewer, extraction, appraisal, and synthesis methods in a protocol; freeze it before searching or activating the run.
- Invoke acquisition, classification (`classify_text` / `classify-existing`), verification, distillation, and synthesis roles. Provider comparison is agreement only; use the held-out human-gold evaluation before changing unattended classification policy.
- Keep search hits as candidates until acquisition; preserve every nonempty search export and hash in systematic runs.
- Require independent human screening and extraction, protocol-defined adjudication, appraisal, and report validation. General claim verification does not replace these steps.
- Do not describe bounded discovery as exhaustive or claim PRISMA compliance from a generated flow summary.
- Record events for phase transitions where the event interface is implemented. Research-method record functions do not yet emit events for every operation.
- Handle retries, circuit breakers, and budget management.
- Emit final synthesized output with full provenance trace.

## Triggers

- Orchestrator assigns a run to `research-agent`.
- A human operator submits a new brief or adds research scope to `knowledge-base/01-project/brief.md`.

## Output

- Final report with `claim → evidence → source` trace.
- For systematic reviews: protocol-bound search, screening, appraisal, extraction, flow, deviations, limitations, and audit-report reference.
- All task records updated.
- Event records for supported phase transitions; do not represent the event log as complete provenance for all method records.
