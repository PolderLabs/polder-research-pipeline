---
type: project
status: draft
tags:
  - project
  - brief
  - goals
---

# Project Brief

The Polder Research Pipeline is a repository-native framework for structured, agent-driven research.

## Mission

Build a reusable research operating system that can start from an arbitrary project, question, investigation, or subject and autonomously:
1. Plan research
2. Discover and acquire sources
3. Process heterogeneous material
4. Extract claims, entities, measurements, relationships, limitations, and open questions
5. Classify and link evidence
6. Verify important claims
7. Maintain a structured knowledge base
8. Answer questions with precise source-backed responses
9. Track agent actions and repository state
10. Detect stale, changed, contradictory, or unsupported knowledge
11. Decide when maintenance or re-research is necessary
12. Evolve its ontology and workflow in a controlled, auditable way

## Architecture principles

- **Structured state is authoritative**: `.research/` JSON records, not Markdown
- **Markdown is a projection**: human-readable view of structured state
- **Events are append-only**: no overwriting history
- **Provenance is mandatory**: every claim traces to a source
- **Schema registry is the single source of truth**: for vocabulary, status enums, transition rules
- **Tests are evidence**: assertions prove behavior, not implementation

## Current phase

P0–P3 implementation: making the repository truthful, establishing conventions, building the control plane, and setting up CI.

## Constraints

- The system MUST NOT fabricate citations or answers outside the established knowledge base
- External research content is treated as untrusted
- Obsidian is a UI, not authoritative workflow state
- Superseded implementations are removed, not kept in parallel
