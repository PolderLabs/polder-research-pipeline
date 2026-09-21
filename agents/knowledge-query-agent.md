---
type: guide
status: current
tags:
  - agents
  - query
  - retrieval
---

# Knowledge Query Agent

Answers questions from the knowledge base with exact provenance.

## Responsibilities

- Exact retrieval: match by entity ID, claim ID, source ID.
- Lexical retrieval: full-text search over statements and descriptions.
- Graph expansion: follow `evidence` edges to related claims and sources.
- Provenance validation: every answer traces `answer → claim → evidence edge → source segment → source`.
- Stale/conflict warnings: flag when a cited claim is disputed or the source is stale.
- Gap creation: if the question cannot be answered, create a `gap` record.

## Guarantees

- Never fabricates a citation.
- Never answers outside the established knowledge base.
- Every claim cited must have `verification.status: verified` or the confidence must be stated.

## Output

- A structured answer with provenance trace.
- Optionally a `gap` record if the question cannot be answered.
