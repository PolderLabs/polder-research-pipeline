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
2. **Events are append-only.** Every agent action that changes state MUST emit one event record to `.research/events/`. No overwrites of event history.
3. **Tasks are the unit of work.** No agent operates outside a task. A task record is created before any action is taken.
4. **Idempotency by design.** Every task has an `idempotency_key`. Re-running the same task with the same key produces the same outcome.
5. **Leases prevent collisions.** Before starting a task, an agent acquires a lease. If the lease expires, the task becomes `pending` again.
6. **No unauthorized writes.** Agents read from and write only to the scopes defined in their role manifest.

## State layers

| Layer | Location | Authority |
|---|---|---:|
| Control plane | `.research/events/`, `.research/tasks/`, `.research/runs/`, `.research/handoffs/` | Authoritative |
| Evidence | `.research/sources/`, `.research/claims/`, `.research/entities/` | Authoritative |
| Derived | `.research/state.json`, `.research/health.json` | Derived (rebuildable) |
| Human projection | `00-home/`, `01-project/`, `02-research/`, … | Projection only |

## Task lifecycle

```
pending → leased → in_progress → completed
                    ↘ failed
pending → blocked → (unblock) → pending
```

## Event emission

Every agent MUST emit a typed event for each state transition. Event records go to `.research/events/<timestamp>_<actor>_<event_type>.json`.

## Wikilinks and Markdown

Wikilinks in notes (`[[note]]`) are informational projections. Agents MUST use structured records for all state operations. The Obsidian vault is never locked or treated as a authoritative data store.

## Tool contract

Any tool invoked by an agent MUST:
- Be named in the agent's role manifest.
- Validate all inputs against schemas before writing.
- Emit a `tool.called` or `tool.failed` event.
- Never suppress errors — surface them to the calling agent.
