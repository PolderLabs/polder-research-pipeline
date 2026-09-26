---
type: system
status: current
tags:
  - decisions
  - classification
  - workflow
---

# Bounded decision workflows

`polder-research decision-run` sends a bounded JSON state object to a configured
provider, checks its response against a versioned question pack, and records a
provider attempt plus a deterministic policy result. It returns a proposal. It
does not edit a source, claim, task, screening, extraction, or appraisal record.

## Workflows

| Workflow | Use | Boundary |
|---|---|---|
| `intake-triage` | Suggest intake labels | Does not accept or reject a source |
| `task-routing` | Suggest a role from the supplied `--role` shortlist | Does not create a handoff or assign a task; validate the suggestion against the role manifest |
| `extraction-quality` | Flag extraction records for human attention | Does not replace independent extraction or adjudication |
| `source-priority` | Order sources for ongoing, bounded discovery | Available only for `continuous_intelligence`; never use to screen a systematic review |
| `review-priority` | Order a human review queue | Does not change review outcomes |

## Run a workflow

The command requires a JSON file containing only the fields needed for the
chosen question pack. The file's content is not copied into attempt records,
but its hash, submitted character count, provider, model, question-pack hash,
and operational metadata are retained under `.research/`.

```sh
polder-research --root ./my-research decision-run \
  --workflow intake-triage \
  --target-kind source \
  --target-id src_<uuid> \
  --state-json ./triage-input.json \
  --sensitivity public
```

Laya is the default local provider. Jev uses the hosted TypeSafe API and is
available only when project configuration, question-pack policy, and explicit
remote approval allow the request. Sensitive or personal data is blocked from
Jev. Choose the smallest sufficient input and review the privacy policy before
using a remote provider. Provider failure does not trigger fallback to another
provider.

## Interpret the result

Each run appends a record to `.research/decision_attempts/` and a policy result
to `.research/decision_policy_results/`. These records retain hashes and
provider metadata, not submitted text. Retries are linked to earlier attempts
with the same request fingerprint.

Provider confidence is not calibrated correctness. The current policy has no
held-out correctness calibration, so it returns `review` for each field and
does not automatically apply a decision. A `completed` provider attempt means
the response passed structural validation; it does not mean its proposal is
correct or accepted.

The CLI prints the recorded attempt and returns:

- `0` when the provider attempt completed;
- `1` when the provider or response failed;
- `2` when privacy policy blocked the request.

The JSON status and `error_category` explain nonzero outcomes. Review the
failure before retrying. Do not treat a failed or blocked attempt as a completed
decision.

## Agent boundary

The Decision Agent role owns these bounded proposals. Its role manifest
describes intended actions and data scope, but it does not enforce filesystem
authorization. Task routing is advisory: a caller must re-check the selected
role against the manifest before creating a handoff. See the
[[03-system/agent-capabilities|capability map]] for implemented interfaces.
