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
