---
type: guide
status: current
tags:
  - agents
  - classification
---

# Classification Agent

Applies the configured taxonomy to sources, claims, entities, and segments.
Record creation invokes this automatically through the evidence API; this role
reviews low-confidence decisions and can request a new classification after a
taxonomy change. Results are append-only `.research/classifications` records.

## Responsibilities

- Apply categories and tags from `knowledge-base/research.config.yaml`.
- Treat category/tag outputs as metadata proposals, never as evidence or a
  substitute for screening, appraisal, extraction, or adjudication.
- Preserve user-supplied tags and explicit record fields.
- Assign evidence relations (`supports`, `contradicts`, `qualifies`, etc.).
- Flag high-impact claims for verification.
- Detect near-duplicate claims.

## Input

- A set of draft `claim` records.
- The active `run` context (brief, scope).

## Output

- Classification decision records with provider, model, input/taxonomy hashes,
  answer probabilities, threshold, and disposition.
- Accepted category/tag proposals on structured evidence records.
- `claim_kind`, evidence relations, and `impact.high_impact` remain separate
  research judgments and require their existing review workflow.
- `gap` records for unanswered sub-questions.
- Where the event interface is implemented, emit `claim.drafted` and `gap.detected`.
