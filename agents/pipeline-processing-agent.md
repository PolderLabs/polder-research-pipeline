---
type: guide
status: current
tags:
  - agents
  - processing
---

# Pipeline Processing Agent

Extracts and segments raw source material into structured records.

## Responsibilities

- Parse raw source (PDF, HTML, Markdown, JSON, etc.).
- Split into `segment` records with exact locators (page, paragraph, line, etc.).
- Extract named entities → `entity` records.
- Extract structured claims → `claim` records (draft status).
- For systematic reviews, keep general claim authoring separate from protocol-defined data extraction. Record required fields with supporting segments through the research-method API and do not replace duplicate independent extraction with a single agent's draft.
- Route segments to classification agent.

## Input

- One `source` record.
- A `task` with `task_kind: process`.

## Output

- Zero or more `segment` records in `.research/segments/`.
- Zero or more `entity` records in `.research/entities/`.
- Zero or more draft `claim` records in `.research/claims/`.
