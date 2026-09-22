---
type: source
status: current
tags:
  - sources
  - reference-catalog
---

# Reference Catalog

Human-readable projection of registered sources. Authoritative structured source records live in `.research/sources/`.

## Authority rule

## Catalog

| Source ID | Title | Type | Retrieved | Status | Content SHA-256 | Related note |
|---|---|---|---|---|---|---|

## Registration rules

- One row per canonical `src_` record.
- Deduplicate in this priority order: DOI → repository URL + commit → canonical URL → content SHA-256.
- Keep titles as published by the source.
- Record retrieval timestamp in ISO 8601 UTC.
- Preserve exact content hash; never silently replace a source record when content changes.
- Use `superseded` to preserve identity history.

## Citation format

Every durable claim should be traceable to:

`claim → evidence edge → segment/locator → source record`

For PDF sources: include page number or section. For web sources: include canonical URL and retrieval timestamp. For repositories: include repository URL and commit SHA. For video/audio: include timestamp range.
