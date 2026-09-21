---
type: guide
status: current
tags:
  - agents
  - cleanup
  - sorting
---

# Sorting & Cleanup Agent

Maintains the structural integrity of the vault and derived state.

## Responsibilities

- Detect orphan notes (no incoming links).
- Detect broken references (target does not exist).
- Detect stale content (content older than freshness threshold).
- Detect frontmatter drift (type/status not matching domain convention).
- Detect duplicate records.
- Emit `gap` records for unresolved orphaned links.

## Triggers

- Scheduled maintenance (daily).
- Human operator request.
- Post-run cleanup phase.

## Output

- Reports written to `.research/maintenance/`.
- Events: `maintenance.triggered`, `maintenance.completed`.
