---
type: guide
status: current
tags:
  - agents
  - control-plane
---

# Agent Contract

Every agent in the Polder Research Pipeline — human or autonomous — MUST follow this contract. The contract defines how agents discover state, claim work, record provenance, and hand off to other roles.

## Principles

1. **Structured state is authoritative.** The `.research/` directory holds JSON records. Markdown notes are a human-facing projection of that state, never the reverse.
2. **Events are append-only.** Use the event API for every supported state transition. Do not imply that a helper emits an event unless its implementation does so; event coverage is not yet complete for every research-method record writer.
3. **Tasks are the workflow unit.** The operating model assigns work through task records; not every current API requires or validates a task ID.
4. **Idempotency by design.** Use an `idempotency_key` where the task API supports it. This is not a guarantee that every research-method operation is replay-idempotent.
5. **Leases reduce collisions.** Use task leases where the workflow supports them. They do not currently provide a general authorization boundary for all record writers.
6. **Respect role scopes.** Role manifests document intended capabilities; runtime authorization does not currently enforce every manifest boundary.

## State layers

| Layer | Location | Authority |
|---|---|---:|
| Control plane | `.research/events/`, `.research/tasks/`, `.research/runs/`, `.research/handoffs/` | Authoritative |
| Evidence and provenance | `.research/sources/`, `.research/segments/`, `.research/claims/`, `.research/entities/`, `.research/edges/`, `.research/gaps/`, `.research/conflicts/` | Authoritative |
| Review method | `.research/protocols/`, `.research/searches/`, `.research/candidates/`, `.research/screenings/`, `.research/extractions/`, `.research/appraisals/` | Authoritative, local-only |
| Reports and snapshots | `.research/reports/`, `.research/state.json`, `.research/health.json` | Reports are generated audit indexes; state/health are derived |
| Human projection | `00-home/`, `01-project/`, `02-research/`, … | Projection only |

## Task lifecycle

```
pending → leased → in_progress → completed
                    ↘ failed
pending → blocked → (unblock) → pending
```

## Research method selection

Use `continuous_intelligence` for ongoing, bounded discovery and maintenance. Use `systematic_evidence_review` only when the question requires a prespecified review. For systematic runs, follow `knowledge-base/00-home/research-methods.md`: freeze a protocol before activation, preserve search exports, keep candidates separate from acquired sources, record independent human decisions and adjudication, and satisfy the completion validator before completing the run. Protocol reviewer IDs document roles but are not authenticated identities.

Independent screening and extraction require genuinely independent human reviewers. The system validates protocol-listed reviewer IDs but cannot verify who entered them or authenticate that independence.

## Event emission

Where event APIs exist, event records go to `.research/events/`. Do not hand-author event records or claim full event coverage until it is implemented and verified.

## Wikilinks and Markdown

Wikilinks in notes (`[[note]]`) are informational projections. Agents MUST use structured records for all state operations. The Obsidian vault is never locked or treated as an authoritative data store.

## Tool contract

Any tool invoked by an agent MUST:
- Be named in the agent's role manifest.
- Validate all inputs against schemas before writing.
- Emit a `tool.called` or `tool.failed` event when the event interface is available; do not claim that every current API emits tool events.
- Never suppress errors — surface them to the calling agent.
