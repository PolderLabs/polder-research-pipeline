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
- Route segments to classification agent.

## Input

- One `source` record.
- A `task` with `task_kind: process`.

## Output

- Zero or more `segment` records in `.research/segments/`.
- Zero or more `entity` records in `.research/entities/`.
- Zero or more draft `claim` records in `.research/claims/`.
