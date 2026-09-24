---
type: guide
status: current
tags:
  - evidence
  - model
  - knowledge-base
---

# Evidence Model

How claims, evidence, and sources are structured in the Polder Research Pipeline.

## Core hierarchy

```
systematic review protocol (prm_)
  └── search execution (sea_)
       └── search candidate (can_) — includes duplicates and exclusions before acquisition
            └── source (src_)       — acquired artifact with content hash
  └── segment (seg_)         — verbatim passage, pinned locator
       └── claim (clm_)      — structured statement
            └── evidence     — directed edge to source segment
                 └── relation: supports | contradicts | ...
```

## Source

One canonical record per distinct research artifact. Fields:
- `id` (src_ UUIDv7)
- `schema_version`
- `source_status`: current | stale | superseded | archived | retracted
- `source_type`: paper | documentation | repository | webpage | dataset | benchmark | ...
- `media_type`: pdf | html | markdown | text | json | csv | ...
- `content_sha256` — computed from raw bytes
- `byte_size`, `mime_type`
- `retrieved_at`, `last_checked_at`
- `freshness.volatility`, `freshness.review_after`
- `lineage[]`: cites | mirrors | republishes | summarizes | forks | derives_from | ...
- `independence_group`: sources with shared authorship/editorial control

Search hits are not sources until an artifact has been acquired and hashed. Systematic-review candidate, screening, extraction, appraisal, and report records preserve the pre-acquisition selection history.

## Segment

A verbatim passage from a source, referenced by a stable locator:
- `locator.scheme`: page | section | paragraph | line | timestamp | chapter | anchor | byte-offset | sha256
- `locator.value`, `locator.start`, `locator.end`
- Segments are immutable. To supersede: create a new segment, update the claim.

## Claim

A structured, verifiable statement:
- `statement`: natural language
- `claim_status`: draft | verified | disputed | refuted | superseded | archived
- `claim_kind`: factual | quantitative | comparative | causal | predictive | definitional | methodological | opinion
- `evidence[]`: each edge has `relation`, `source_id`, `segment_id`, `directness`, `confidence`, `locator`
- `verification`: status, checks_performed[], verified_at, verified_by
- `impact.high_impact`: boolean — triggers mandatory verification

## Evidence directness

- **primary**: source makes the claim directly
- **secondary**: source reports someone else's claim
- **tertiary**: source cites a source that cites a claim
- **unknown**: directness not determined

Do not count derivative reporting as independent evidence.

## High-impact claims

Claims flagged `impact.high_impact: true` MUST receive:
1. Verification of source supporting the claim
2. Locator validation
3. Version/date/unit consistency check
4. Scope matching
5. Source independence verification
6. Primary evidence check
7. Disconfirming search (seek contradicting evidence)
8. Freshness check

Systematic review extraction is separate from claim authoring: each prespecified field is independently extracted by two protocol-listed human reviewers, linked to a segment, and adjudicated when values differ. Appraisal records retain instrument-specific domain judgments and rationales; they are not represented by evidence-edge confidence.

## Conflict detection

When two claims with `claim_status: verified` have contradictory evidence edges, a `conflict` record is created with `severity: critical`. The conflict blocks decisions that depend on either claim until resolved.

## Answer provenance trace

Every answer from the knowledge base MUST trace: `answer → claim → evidence edge → segment → source`.
