---
type: guide
status: current
tags:
  - methodology
  - systematic-review
  - reproducibility
---

# Research Methods and Auditability

The pipeline supports two distinct research modes. A run must not claim systematic coverage unless it uses the protocol-first workflow below.

## Choose the method honestly

- **Continuous intelligence** is ongoing, non-exhaustive monitoring. Record source provenance, content hashes, claim-level evidence, uncertainty, conflicts, and freshness. State that coverage is bounded by what was monitored.
- **Systematic evidence review** is a prespecified, reproducible review. It requires a frozen protocol, exact database/platform queries, saved result exports, explicit candidate deduplication, two independent human screening decisions, adjudication of disagreements, duplicate extraction, structured appraisal, and a generated audit report before completion.

PRISMA 2020 and PRISMA-S are reporting guidance for systematic reviews; a flow chart or checklist does not by itself make a review systematic. The implementation produces a PRISMA-style record flow summary and auditable search records. It is not a PRISMA compliance certificate, and it does not imply that every possible database or source was searched. Cochrane guidance supports prespecifying eligibility and synthesis, explaining protocol changes, independent selection/extraction, and retaining reasons for decisions. Use the method that fits the question and evidence base; do not apply health intervention frameworks mechanically to technology research.

## Systematic review lifecycle

1. Create a run with `research_method="systematic_evidence_review"` and a clear question.
2. Create a draft protocol that states objectives, question framework (PICO, PECO, PCC, SPIDER, or a justified custom frame), inclusion/exclusion criteria, the search cutoff, each database and platform, exact query strings and limits, independent reviewers, adjudication rule, extraction fields, appraisal instrument/version/reference, and planned synthesis/heterogeneity/sensitivity handling. Explain framework and instrument fit for the research question and evidence type.
3. Freeze the protocol before activating the run. The pipeline hashes the canonical protocol and binds that digest to the run. After activation, protocol edits invalidate the run; create a new run for a changed protocol.
4. Execute every planned query and record its timestamp, operator, platform, exact query, search software/version, and result count. Every nonempty search must include the location and SHA-256 of a saved results export. Record every returned item as a candidate, including duplicates; acquired sources are separate records and require a captured artifact/hash.
5. Each protocol-listed human reviewer records title/abstract and, where eligible, full-text decisions independently. Use only the protocol's exclusion reasons. An independent human adjudicator resolves disagreement and references the decisions being resolved. AI can assist discovery or summarize material, but it does not count as either independent human reviewer.
6. For included full texts, two independent reviewers extract every prespecified field. Each reported value must cite a segment from the acquired source; use `not_reported` or `unclear` rather than inventing a value. Record and adjudicate differences while retaining both original extractions.
7. Record appraisal by the instrument named in the protocol. Keep domain judgments, rationales, and limitations; do not compress study quality or certainty to an unsupported single score. Use a certainty framework such as GRADE only when it is appropriate to the question and evidence type.
8. Synthesize using the planned groups and method. Keep incompatible measurement setups separate, report uncertainty and limitations, and preserve contradictions. Every knowledge claim should trace through an evidence edge and segment to the immutable source.
9. Generate the machine-readable audit report and complete the run. Completion checks derive search coverage, screening flow, extraction completeness, appraisals, protocol binding, and report freshness from the records; counts are not hand-entered authority.

The Python API is in `polder_research.research_methods`: `create_protocol`, `freeze_protocol`, `record_search`, `register_candidate`, `record_screening_decision`, `adjudicate_screening`, `record_extraction`, `adjudicate_extraction`, `record_appraisal`, `generate_review_report`, and `validate_run_for_completion`. `runs.update_run_status(run_id, "active")` requires a frozen protocol for systematic runs; transition to `completed` runs the evidence and report checks.

## Evidence and provenance rules

- Search results that have not been acquired are **candidates**, not sources. This preserves excluded and duplicate records without weakening the source content-hash requirement.
- Source-reported findings, direct observations, and inferences remain distinct. A source's claim is not independent corroboration merely because another source repeats it.
- Segments retain locators. Claims and extracted values without a traceable passage stay unverified.
- Appraisal is instrument- and domain-specific. Edge confidence, claim verification, risk of bias, and certainty of an overall body of evidence are different concepts.
- Protocol, search, candidate, screening, extraction, appraisal, and report records are schema-validated and atomically written. The audit report hashes the records it indexes so later edits make it stale.
- The completion gate requires at least one appraisal for each included source when the protocol marks appraisal required. It does not enforce duplicate independent appraisal or validate the domain logic of a custom instrument; teams that need independent appraisal must ensure it in their protocol and report it explicitly.
- Research-method record writers do not yet emit an event for every operation. The typed records and review report are the primary method audit trail; the event stream is not a complete substitute.

## Reproducibility boundary

Authoritative `.research/` records are currently local-only and gitignored. Reviewer IDs are labels and are not authenticated. A run can therefore be internally auditable in the same repository state, but it is not collaborator-reproducible from a fresh clone until those records and raw result exports are placed in a shared durable backend or exported archive. The generated report indexes record hashes but does not bundle raw evidence. Search engines may also change results over time; saved exports, query text, date, platform, and hashes preserve what this run actually observed, not a guarantee that a future live query returns identical results.

## Standards and guidance

- [PRISMA 2020 checklist](https://www.prisma-statement.org/prisma-2020-checklist) — systematic review reporting, including selection counts and excluded reports.
- [PRISMA-S](https://www.prisma-statement.org/prisma-search) — reporting database searches and search methods.
- [Cochrane Handbook: searching and study selection](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04) — comprehensive searches and independent selection.
- [Cochrane Handbook: protocol and reporting](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-iii) — prespecified methods and explained amendments.
- [Cochrane Handbook: data collection](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-05) — independent duplicate extraction and disagreement handling.
- [W3C PROV Data Model](https://www.w3.org/TR/prov-dm/) — entities, activities, agents, attribution, and derivation.
- [FAIR Guiding Principles](https://doi.org/10.1038/sdata.2016.18) — findable, accessible, interoperable, reusable data and provenance.

These sources were checked on 2026-09-24. PRISMA/Cochrane are used here as methods and reporting references, not as universal standards for all technology landscape work.

## Related

- [[evidence-model|Evidence model]]
- [[provenance-model|Provenance model]]
- [[research-intake-guide|Research intake guide]]
