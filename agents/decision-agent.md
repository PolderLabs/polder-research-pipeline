---
type: guide
status: current
tags:
  - agents
  - decisions
  - classification
---

# Decision Agent

Runs bounded, provider-backed workflows that help people sort and prioritize
research work. This role proposes metadata and queue order; it does not make
research findings or change source, claim, screening, extraction, or appraisal
records.

## Available workflows

- `intake-triage` proposes labels for a source or intake item.
- `task-routing` suggests one role from the supplied role list. A caller must
  validate the suggestion against the role manifest before assigning work.
- `extraction-quality` flags extraction records for human attention. It does
  not replace duplicate independent extraction or adjudication.
- `source-priority` orders sources for continuous intelligence only. It cannot
  screen or exclude systematic-review candidates.
- `review-priority` orders a human review queue. It does not change review
  outcomes.

## Privacy and policy

Run `polder-research decision-run --help` for the complete command interface.
The command reads the supplied JSON state file and records its hash, not the
state text, in the provider-attempt record. Keep that file bounded to the
minimum information needed. Laya is the default local provider. Jev sends input
to TypeSafe only when project policy, workflow policy, and explicit remote
approval allow it; sensitive and personal data are blocked.

Provider scores are not calibrated correctness. Until a matching held-out
calibration is available, the policy result keeps fields in `review` and does
not apply them automatically. Decision attempts and policy results are
append-only records under `.research/decision_attempts/` and
`.research/decision_policy_results/`.

## Failure handling

The CLI prints the persisted attempt status and returns `0` for `completed`,
`1` for `failed`, and `2` for `blocked`. A nonzero exit is not a completed
decision. Inspect `error_category`, correct the configuration or privacy issue,
and retry deliberately. Provider failures do not silently fall back to another
provider.
