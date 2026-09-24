---
type: guide
status: current
tags:
  - agents
  - classification
---

# Classification Agent

Applies the configured research taxonomy to sources, claims, entities, and
segments. The evidence registration API classifies new records synchronously;
`polder-research classify-existing` replays current provider configuration over
existing records. Results are immutable `.research/classifications` records.
Use `classification-compare` for matched provider agreement and
`classification-evaluate` only with separately maintained human labels.

The local dashboard's review inbox records immutable field-level human review
decisions. Reviewer names are self-reported, not authenticated. A review record
does not rewrite the original provider output. Accepted fields may be applied
automatically during new registration; uncertain fields remain proposals.

## Responsibilities

- Apply categories, tags, and controlled dimensions from
  `knowledge-base/research.config.yaml`.
- Enforce routing rules for record kind and privacy labels. Jev uses the hosted
  TypeSafe API; Laya inference is local. Internal, confidential, restricted,
  and personal-data records must not be sent to Jev.
- Validate returned option sets and probabilities and preserve each field's
  accepted, rejected, review-required, or abstained status.
- Treat category/tag outputs as metadata proposals, never as evidence or a
  substitute for screening, appraisal, extraction, or adjudication.
- Preserve user-supplied tags and explicit record fields.
- Do not assign evidence relations, verify claims, or mark systematic-review
  screening/appraisal outcomes through classification. These remain separate
  research-method tasks with their own human review requirements.

## Input

- A source, claim, entity, or segment and its locatable extracted text.
- Its inherited privacy metadata and the active taxonomy/question-set version.

## Output

- Classification decision records with provider, model, input/taxonomy hashes,
  answer probabilities, threshold, and disposition.
- Accepted fields are applied on initial record registration without replacing
  existing user metadata. Uncertain fields are not silently applied.
- `classification-evaluate` reports performance against a frozen held-out human
  gold set; provider agreement alone is not evidence of accuracy.
- `claim_kind`, evidence relations, `impact.high_impact`, and `gap` records are
  separate research judgments and are not created by the classification tools.

## Runtime limits

The role manifest describes intended agent scope; it is not runtime
authorization. Current classification APIs and commands are documented in
[[knowledge-base/03-system/classification-providers|provider setup]] and
[[knowledge-base/03-system/classification-operations|operating standards]].
Systematic screening, appraisal, and claim adjudication retain their own
protocol and independent-review controls.
