---
type: guide
status: current
tags:
  - agents
  - verification
---

# Verification Agent

Verifies high-impact claims against primary evidence.

## Responsibilities

- For each high-impact claim, verify:
  - The source actually supports the claim.
  - The locator (page, paragraph) is correct.
  - Version, date, and unit are consistent.
  - The scope matches the claim.
  - Source independence where claimed.
  - Primary evidence is available.
- Seek contradicting evidence (disconfirming searches).
- Check freshness against source volatility policy.
- Update `claim.verification` field.

## Input

- A set of `claim` records with `impact.high_impact: true`.

## Output

- Updated `claim` records with `verification.status` set.
- Events: `claim.verified`, `claim.disputed`, `claim.refuted`.
