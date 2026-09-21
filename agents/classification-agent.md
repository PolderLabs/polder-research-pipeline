---
type: guide
status: current
tags:
  - agents
  - classification
---

# Classification Agent

Classifies claims and segments for routing and priority.

## Responsibilities

- Classify each claim by `claim_kind` (factual, quantitative, causal, etc.).
- Classify each segment by relevance to the active brief.
- Assign evidence relations (`supports`, `contradicts`, `qualifies`, etc.).
- Flag high-impact claims for verification.
- Detect near-duplicate claims.

## Input

- A set of draft `claim` records.
- The active `run` context (brief, scope).

## Output

- Updated `claim` records with `claim_kind`, `relation`, and `impact.high_impact`.
- `gap` records for unanswered sub-questions.
- Events: `claim.drafted`, `gap.detected`.
