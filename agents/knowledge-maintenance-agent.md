---
type: guide
status: current
tags:
  - agents
  - maintenance
---

# Knowledge Maintenance Agent

Keeps the knowledge base current by monitoring and refreshing sources and claims.

## Responsibilities

- Enforce freshness policies per source.
- Re-check stale claims.
- Detect changed, retracted, or updated sources.
- Re-verify claims whose supporting sources have changed.
- Detect new conflicts.
- Trigger gap-filling for newly identified gaps.

## Freshness policy

- Security advisories: very short (hours).
- Pricing, benchmarks: short (days).
- Software releases: moderate (weeks).
- Peer-reviewed papers: long (months).
- Pinned standard versions: event-triggered.
- Historical facts: stable (annual review).

## Triggers

- Scheduled (per source freshness policy).
- Source refreshed event.

## Output

- Updated `claim` and `source` records.
- `conflict` records if contradictions detected.
- Events: `source.refreshed`, `maintenance.triggered`.
