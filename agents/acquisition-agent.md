---
type: guide
status: current
tags:
  - agents
  - acquisition
---

# Acquisition Agent

Acquires and ingests raw research material.

## Responsibilities

- Discover sources (web search, API, GitHub, arXiv, etc.).
- Download and store raw material.
- Register a `source` record with `content_sha256`, byte size, MIME type, and retrieval timestamp.
- Verify immutability: confirm the raw file matches its registered hash.
- Deduplicate against existing source records.

## Input

- A `task` with `task_kind: acquire`.
- May carry a list of target URLs, keywords, or DOIs.

## Output

- One or more `source` records in `.research/sources/`.
- Raw file stored at the path indicated in `raw_location`.
- Events: `source.discovered`, `source.acquired`, `source.hash-verified`.
