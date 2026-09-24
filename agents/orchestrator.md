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
2. Choose and record the run method: `continuous_intelligence` or `systematic_evidence_review`.
3. For a systematic review, create and freeze the protocol, then bind its hash to the run before activation.
4. Decompose the brief into `task` records and assign them via typed `handoff` records.
5. Monitor task completion and handle failures. Systematic runs also require a generated review report and clean `validate_run_for_completion` result.
6. Close only when the applicable completion gate is satisfied; otherwise record the blocker or failure.

## Triggers

- Human operator creates a run.
- Scheduled maintenance run (daily health check).

## Exits

- Run completes: all tasks resolved.
- Run aborted: human operator cancels.
- Run failed: unrecoverable error in orchestrator itself.
