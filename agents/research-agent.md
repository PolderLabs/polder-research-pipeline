---
type: guide
status: current
tags:
  - agents
  - research
---

# Research Agent

The research agent drives a research brief end-to-end using specialist sub-agents. It is the primary autonomous interface for human operators.

## Responsibilities

- Execute a run against a brief.
- Invoke acquisition, classification, verification, distillation, and synthesis agents.
- Record events for each phase transition.
- Handle retries, circuit breakers, and budget management.
- Emit final synthesized output with full provenance trace.

## Triggers

- Orchestrator assigns a run to `research-agent`.
- A new brief is registered in `01-project/questions.md`.

## Output

- Final report with `claim → evidence → source` trace.
- All task records updated.
- Events emitted for every phase.
