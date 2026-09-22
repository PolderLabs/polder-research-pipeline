---
type: guide
status: current
tags:
  - glossary
  - vocabulary
  - definitions
---

# Glossary

Canonical definitions for the Polder Research Pipeline.

## Claim

A structured, verifiable statement extracted from a source and linked to evidence. Claims have a `claim_status` of `draft`, `verified`, `disputed`, `refuted`, `superseded`, or `archived`. Every claim MUST be traceable to at least one source.

## Source

A distinct research artifact — paper, webpage, dataset, benchmark, repository, video, book, or other — registered with a stable `src_` ID and a content SHA-256 hash. One canonical source record per distinct artifact.

## Evidence

A directed edge from a claim to a source segment. Evidence has a `relation` in `{supports, contradicts, partially-supports, qualifies, contextualizes, updates, supersedes}` and a `directness` in `{primary, secondary, tertiary, unknown}`.

## Entity

A named thing — model, tool, dataset, organization, person, standard, benchmark, or concept — registered with a stable `ent_` ID. Entities are deduplicated globally; aliases are linked to the canonical entity.

## Hypothesis

A tentative claim proposed as a basis for investigation, distinct from a verified claim.

## Segment

A verbatim passage from a source, pinned by a stable locator (page, paragraph, line, timestamp, byte-offset, etc.). Segments are immutable once created.

## Gap

An explicit unanswered question or missing evidence in the knowledge base. Gaps have a `priority` and a `status`. A gap is filled when a claim with `verification.status: verified` addresses it.

## Conflict

Two or more claims that contradict each other, with at least one evidence edge supporting each side. Conflicts have a `severity` and `status`. A conflict is resolved when evidence determines which claim is correct, or when both are found to be scoped differently.

## Provenance

The complete chain from a claim to the raw source: `claim → evidence edge → segment → source`. Provenance MUST be preserved and verifiable. Every claim in the knowledge base MUST be able to answer "why do we believe this, from exactly where, under which version/scope?"

## Freshness

A per-source policy defining how often the source should be re-checked. Freshness is determined by `volatility` and `review_after`. Volatility ranges from `very-short` (hours) for fast-moving content (security advisories) to `stable` (annual review) for historical facts. No universal 90-day rule.

## Run

One bounded research session against a brief. A run groups related tasks, tracks budget, and records start/finish timestamps. Runs are `draft → active → completed/aborted/failed`.

## Task

One unit of work within a run. Tasks are `pending → leased → in_progress → completed`. A task MUST be owned by exactly one role at a time; leases prevent collisions.

## Handoff

A typed transfer of work between roles. Handoffs are `open → accepted/rejected/expired`. A handoff carries context and optional artifacts.

## Verification

The process of checking that a source actually supports its assigned claims. High-impact claims MUST be verified. Verification checks: source supports claim, locator valid, version/date/unit consistent, scope matches, source independence where claimed, primary evidence available, contradicting evidence sought, freshness checked.

## Evidence label

How a claim's support was obtained:
- **Observed** — measured directly in this research
- **Source-reported** — stated by a source without independent verification
- **Inference** — logically derived from other evidence

## Control plane

The structured state layer: `.research/events/`, `.research/tasks/`, `.research/runs/`, `.research/handoffs/`, `schemas/`, `agents/`, `research.config.yaml`. Authoritative for workflow state.

## Human projection

The Markdown/Obsidian vault — `00-home/`, `01-project/`, etc. A human-readable projection of the control plane. NOT authoritative for workflow state.
