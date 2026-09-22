---
type: inbox
status: current
tags:
  - intake
  - manifest
---

# Intake Manifest

Queue and lifecycle tracker for raw material in `90-inbox/`. Every drop registers here before processing.

## Queue

| Item | Kind | Added | Status | Owner | Outcome |
|---|---|---|---|---|---|

<!-- Rows are appended by `intake_register.py`. Status lifecycle: new → triaged → processing → distilled → filed (or rejected at any point). -->

## Status lifecycle

- **new** — dropped, not yet reviewed.
- **triaged** — type, domain, and decision impact assessed.
- **processing** — processing note created, claims being extracted.
- **distilled** — durable note created or updated, source catalog updated.
- **filed** — processing record archived in `90-inbox/archive/filed/`.
- **rejected** — intentionally not incorporated, archived in `90-inbox/archive/rejected/`.

## Columns

- **Item**: descriptive name or short title.
- **Kind**: file type (pdf, url, video, transcript, benchmark, etc.).
- **Added**: ISO date the item was registered.
- **Status**: lifecycle state (see above).
- **Owner**: agent or person responsible for processing.
- **Outcome**: path to durable note, conflict note, or rejection reason.
