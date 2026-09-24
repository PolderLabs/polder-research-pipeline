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
- **Typed record contracts**: JSON Schemas define record structure; some vocabularies and policy values are also represented in Python and `research.config.yaml`, so updates must keep those surfaces synchronized.
- **Tests are evidence**: assertions prove behavior, not implementation

## Current research modes

- `continuous_intelligence`: bounded ongoing discovery, source processing, verification, and maintenance. It does not claim exhaustive coverage.
- `systematic_evidence_review`: protocol-first workflow with frozen eligibility, search, and synthesis plans; saved hashed search exports; explicit candidates; independent human screening and extraction; adjudication; appraisal; and an audit report.

The workflow is locally auditable. Runtime records are gitignored; reviewer IDs are not identity-authenticated; the report is a hash-indexed inventory rather than a portable archive. See [[00-home/research-methods|Research methods]] for the procedure and standards references.

## Constraints

- The system MUST NOT fabricate citations or answers outside the established knowledge base
- External research content is treated as untrusted
- Obsidian is a UI, not authoritative workflow state
- Superseded implementations are removed, not kept in parallel
