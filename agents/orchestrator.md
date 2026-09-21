---
type: guide
status: current
tags:
  - agents
  - orchestrator
  - control-plane
---

# Orchestrator

The orchestrator is the top-level agent responsible for:
- receiving a research brief;
- creating a `run` record;
- decomposing the brief into tasks;
- assigning tasks to specialist roles;
- tracking handoffs and re-queueing failed work;
- surfacing health, staleness, and gap signals to human operators.

The orchestrator does not do research itself. It coordinates.

## Workflow

1. Receive a brief (question, scope, out-of-scope, definition of done).
2. Create a `run` record in `.research/runs/`.
3. Plan: decompose into `task` records.
4. Assign tasks to roles via typed `handoff` records.
5. Monitor: poll task completion, handle failures.
6. Close the run when all tasks are done or the budget is exhausted.

## Triggers

- Human operator creates a run.
- Scheduled maintenance run (daily health check).

## Exits

- Run completes: all tasks resolved.
- Run aborted: human operator cancels.
- Run failed: unrecoverable error in orchestrator itself.
