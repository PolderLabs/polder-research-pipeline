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
- Keep research-method records and their schemas, task kinds, configuration vocabulary, state-builder discovery, role instructions, and tests synchronized when changing a method contract.
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

- Proposals and migrations are design outputs only: `07-evolution/` is not a configured vault domain or implemented persistence path. Do not claim files were stored there unless that path is added to the canonical layout.
- Where the event interface is implemented, emit `schema.proposed`, `schema.applied`, and `schema.rejected`.
