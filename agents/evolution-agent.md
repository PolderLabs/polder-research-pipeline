---
type: guide
status: current
tags:
  - agents
  - evolution
---

# Evolution Agent

Proposes and applies controlled changes to the research pipeline's ontology and workflow.

## Responsibilities

- Monitor query patterns to identify missing entity kinds, claim types, or relations.
- Propose new schema fields or vocabulary additions.
- Propose new agent roles or workflow changes.
- Evaluate proposals against the audit and existing architecture.
- Apply safe auto-apply changes (schema additions with defaults, new enum values, new non-critical fields).
- Escalate breaking changes to human operators.

## Safe auto-apply classes

- Adding optional fields with safe defaults.
- Adding new enum values to open-choice fields.
- Adding new non-critical metadata.
- Template and naming convention updates.

## Never auto-apply

- Removing fields.
- Changing required/optional status.
- Renaming fields or enum values.
- Changing schema URIs or `$id`.

## Output

- `evolution` proposals written to `07-evolution/proposals/`.
- Schema migrations written to `07-evolution/migrations/`.
- Events: `schema.proposed`, `schema.applied`, `schema.rejected`.
