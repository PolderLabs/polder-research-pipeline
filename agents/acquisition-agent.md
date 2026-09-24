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

- For `systematic_evidence_review`, execute only the frozen protocol's queries. Record exact database/platform, query, execution time, tool/version, result count, and a preserved export location plus SHA-256.
- Register every returned hit as a `candidate` before deduplication/screening. Keep duplicates explicit and link each to its canonical candidate.
- Do not treat an unacquired hit as a `source`; only register a source after capturing its content and hash.
- Discover sources (web search, API, GitHub, arXiv, etc.).
- Download and store raw material.
- Register a `source` record with `content_sha256`, byte size, MIME type, and retrieval timestamp.
- Verify immutability: confirm the raw file matches its registered hash.
- Deduplicate against existing source records.

## Input

- A `task` with `task_kind: acquire` or `task_kind: search`.
- May carry a list of target URLs, keywords, or DOIs.
- Systematic-review tasks also carry the run ID and frozen protocol ID/hash.

## Output

- One or more `source` records in `.research/sources/`.
- Search executions and search-hit candidates in `.research/searches/` and `.research/candidates/`.
- Raw file stored at the path indicated in `raw_location`.
- Emit `source.discovered`, `source.acquired`, and `source.hash-verified` through the event interface where available. Search and candidate record writers do not themselves guarantee an event for every operation.
