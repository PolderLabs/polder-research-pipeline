---
type: template
status: current
tags:
  - template
  - research
---

# {{title}}

## Summary

{{summary}}

## Research question

{{research_question}}

## Method and scope

- **Research mode:** {{continuous_intelligence_or_systematic_evidence_review}}
- **Protocol:** {{protocol_id_or_not_applicable}}
- **Coverage cutoff:** {{search_cutoff_or_monitoring_period}}
- **Deviations and limitations:** {{deviations_and_limitations}}

For systematic evidence reviews, include the generated `.research/reports/` audit reference and summarize its derived search, screening, extraction, and appraisal flow. Do not describe counts as proof of PRISMA compliance.

## Claims

> Classify every claim as **Observed**, **Source-reported**, or **Inference**.

### Claim: {{claim_statement}}

- **Classification:** {{classification}}
- **Evidence:** `{{source_id}}` / `{{segment_id}}`
- **Locator:** {{locator}}
- **Confidence:** {{confidence}}
- **Status:** {{claim_status}}

## Evidence table

| Claim | Source | Segment / locator | Directness | Relation | Verification |
|---|---|---|---|---|---|
| {{claim_id}} | {{source_id}} | {{segment_id}} / {{locator}} | {{primary_or_secondary}} | supports | unverified |

## Entities

| Entity | Kind | Relationship |
|---|---|---|
| {{entity_name}} | {{entity_kind}} | {{relationship}} |

## Limitations

- {{limitation}}

## Open questions

- {{open_question}}

## Related

- {{related_note}}

## Sources

- {{source_citation}}
