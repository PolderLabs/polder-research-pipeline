---
type: system
status: current
tags:
  - agents
  - runtime
  - implementation-status
---

# Agent role and runtime capability map

The `agents/*.md` files define role instructions. `agents/roles/*.yaml` lists
the action names each role may request. `polder_research.agents.require_role`
can check those action names when a caller invokes it, but record writers do
not currently enforce role checks centrally. Manifests neither execute tools
nor secure filesystem access. The YAML `tools` list is limited to implemented
interfaces; `planned_tools` records capabilities that still need an adapter.
Treat a tool as available only when a Python API, CLI command, or dashboard
route implements it.

| Role | Implemented interfaces | Still requires an external agent/tool or is not implemented here |
|---|---|---|
| Orchestrator | Run, task, event, handoff writers; derived workflow state and health | Brief decomposition, agent launch, schedule, and automatic task assignment |
| Acquisition | Protocol/search/candidate record APIs; source registration, content hashing, and `source-acquire` for a captured local artifact | HTTP fetch, Git clone, arXiv retrieval, and vendor/database search clients |
| Pipeline processing | Source, segment, entity, claim, and evidence-edge record APIs | PDF/HTML parsers, extraction models, and automatic claim/entity extraction |
| Classification | `classify_text`, provider routing, existing-record replay, provider agreement report, human-gold evaluation, append-only review decisions, dashboard review inbox | Automatic source acquisition/extraction and claim verification; replay is not an ingestion queue |
| Bounded decisions | `decision-run` for intake triage, task-routing suggestions, extraction quality, continuous-intelligence source priority, and review priority | Automatic task dispatch, screening decisions, extraction adjudication, or calibrated automatic actions |
| Verification | Research-method screening, adjudication, extraction, and appraisal records; protocol/completion validation | General claim verification, disconfirming search client, and automatic claim status updates |
| Research | The underlying structured research-method APIs and run/task APIs | An autonomous end-to-end multi-agent executor |
| Synthesis | Generated systematic-review report from method records | General-purpose report generation from arbitrary claims without an LLM/tool integration |
| Knowledge maintenance | Freshness/maintenance evaluation, health and maintenance record builders | Automatic source refresh, claim re-verification, and scheduled execution |
| Knowledge query | Structured evidence can be read by callers; exact provenance lives in records | Dedicated lexical, semantic, or graph query engine |
| Sorting/cleanup | Vault audit, frontmatter repair, note scaffold, state and health CLI commands | General automatic note filing or content rewrite |
| Evolution | Role contract only | Schema/workflow proposal store and migration executor |

Classification commands are `polder-research classify-existing`,
`classification-compare`, and `classification-evaluate`. Review decisions are
written by the dashboard to `.research/classification_reviews/`; reviewer names
are self-reported. See [[03-system/classification-providers]] and
[[03-system/classification-operations]].

Update this matrix when adding a runtime adapter or changing an agent role. A
role guide must not describe planned tool names as a working automated feature.
Methodological human-review requirements remain governed by
[[00-home/research-methods]], independently of the capability map.

Decision runs write provider attempts and deterministic policy results under
`.research/decision_attempts/` and `.research/decision_policy_results/`.
They return proposals and do not mutate research records. See
[[03-system/decision-workflows]] for input, privacy, and failure behavior.
