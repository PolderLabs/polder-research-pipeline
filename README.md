---
type: guide
status: current
tags:
  - navigation
  - knowledge-base
  - research-pipeline
---

# Polder Research Pipeline

Polder Research Pipeline is an experimental, repository-native framework for building **structured, agent-driven research projects**.

The goal is a reusable research operating system that can be initialized for an arbitrary project, question, technology, literature review, investigation, or subject and then used by humans and specialized agents to:

- plan research;
- discover and acquire sources;
- process heterogeneous research material;
- extract claims, entities, measurements, relationships, limitations, and open questions;
- classify and link evidence;
- verify important claims;
- maintain a structured knowledge base;
- answer questions from that knowledge base with precise source-backed responses;
- track what agents did, when, and why;
- detect stale, changed, contradictory, or unsupported knowledge;
- decide when maintenance or re-research is necessary;
- evolve tags, relationships, search strategies, schemas, and workflow rules in a controlled and auditable way.

The repository currently contains the **initial knowledge-base and research-intake scaffold**. The deeper agent control plane, structured research state, evidence graph, maintenance engine, query agent, and autonomous research workflow are specified in [AUDIT.md](AUDIT.md) but are not implemented yet.

## Current status

This repository is still in the architecture/foundation stage.

Implemented today:

- Obsidian-compatible Markdown knowledge base;
- numbered project/research domains;
- raw research inbox;
- Markdown intake manifest;
- note templates;
- frontmatter conventions;
- link/frontmatter/orphan/tag audit script;
- frontmatter repair helper;
- intake registration helper;
- note scaffolding helper;
- local pre-commit audit hook;
- Dataview-based Obsidian dashboard;
- evidence-origin convention:
  - Observed
  - Source-reported
  - Inference
- conflict-note concept;
- experiment and decision templates;
- detailed structural/agent architecture audit.

Designed but not yet implemented:

- generic project initialization and `research.config.yaml`;
- research briefs and adaptive research plans;
- specialized agent roles;
- knowledge-base query/answer agent;
- machine-readable role capability manifests;
- structured tasks, runs, leases, retries, and handoffs;
- immutable action/event history;
- stable source, claim, entity, gap, and decision IDs;
- canonical source records;
- source fingerprinting and deduplication;
- source segmentation with exact locators;
- claim/evidence graph;
- entity resolution and ontology registry;
- verification/critic workflow;
- automated contradiction detection;
- first-class research gaps;
- source-change impact propagation;
- maintenance scheduling and deterministic triggers;
- schema registry and migrations;
- source adapters;
- autonomous multi-agent orchestration;
- controlled self-evolution;
- CI and conformance fixtures.

For the complete audit, confirmed defects, target architecture, implementation order, and acceptance gates, see [AUDIT.md](AUDIT.md).

---

# What the project is intended to become

The target is not simply “an Obsidian vault that agents edit.”

The intended architecture is:

> **A versioned research data model and agent control plane, with Markdown and Obsidian as one human-facing projection.**

The research flow should eventually look like:

```text
research brief
    ↓
research questions
    ↓
research plan
    ↓
source discovery
    ↓
source acquisition
    ↓
source parsing / segmentation
    ↓
claim + entity extraction
    ↓
classification + linking
    ↓
verification
    ↓
durable knowledge
    ↓
Q&A / synthesis / decisions
    ↓
maintenance + refresh
```

An important conclusion should be traceable through:

```text
answer / report / decision
        ↓
research note or claim
        ↓
claim
        ↓
evidence relation
        ↓
source segment
        ↓
canonical source
```

This traceability is the core quality requirement.

---

# Design principles

## Evidence before synthesis

Search results and snippets are not durable knowledge.

The intended pipeline separates:

1. discovery;
2. acquisition;
3. processing;
4. classification;
5. verification;
6. distillation;
7. synthesis or answering.

## Provenance is mandatory

Important knowledge should be able to answer:

- where did this come from?
- which exact source location supports it?
- which source version was used?
- which agent/tool produced the derived artifact?
- during which research run?
- when was it last verified?
- what later artifact superseded it?

## Contradictions remain visible

Conflicting evidence should not be silently flattened into one conclusion.

The system should preserve:

- competing claims;
- supporting evidence for each;
- date/version/scope differences;
- unresolved uncertainty;
- the research gap needed to resolve the conflict.

## Self-learning means controlled evolution

“Self-learning” here means the repository improves its maintained knowledge and research behavior over time.

Examples:

- canonical aliases;
- entity relationships;
- useful query expansions;
- recurring source locations;
- tag normalization;
- gap prioritization;
- refresh policies;
- source adapters;
- workflow rules.

It does **not** mean agents may silently rewrite schemas, accepted decisions, policies, or disputed conclusions.

High-impact evolution should be explicit, evaluated, recorded, and reversible.

## Machine-readable state, human-readable knowledge

Humans should be able to navigate the research in Markdown.

Agents should not have to infer workflow state from prose.

Tasks, runs, events, source identities, claim identities, maintenance state, and other machine contracts should use structured schemas.

## Obsidian is a presentation layer

Obsidian is currently the richest human interface for the repository.

The future core should also work through:

- filesystem;
- Git;
- Markdown;
- YAML/JSON;
- CLI;
- CI;
- other agent runtimes.

---

# Current quick start

## 1. Clone

```bash
git clone https://github.com/PolderLabs/polder-research-pipeline.git
cd polder-research-pipeline
```

The repository is currently private, so your GitHub account must have access.

## 2. Run the current audit

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py
```

JSON output:

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py --json
```

Current exit behavior:

- `0` — all checks currently implemented by the validator passed;
- `1` — one or more implemented checks failed.

The existing validator does **not yet** cover every repository operating contract. The deeper gaps are documented in [AUDIT.md](AUDIT.md).

## 3. Enable the local Git hook

The pre-commit hook is committed, but Git does not automatically activate repository-local hook paths.

Run:

```bash
git config core.hooksPath .githooks
```

After that, commits run the current vault audit.

A future bootstrap command should automate this.

## 4. Optional: open in Obsidian

Use the repository root as the Obsidian vault.

The current dashboard is [index.md](index.md).

The enhanced dashboard expects Dataview and uses:

```text
.obsidian/snippets/polder-dashboard.css
```

The long-term architecture will keep Obsidian optional.

---

# Current repository structure

```text
.
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── AUDIT.md
├── index.md
│
├── 00-home/
├── 01-project/
├── 02-research/
├── 03-system/
├── 04-decisions/
├── 05-operations/
├── 06-sources/
│
├── 90-inbox/
│   ├── raw/
│   ├── processing/
│   ├── archive/
│   └── manifest.md
│
├── 99-templates/
│
├── skills/
│   └── obsidian-knowledgebase-curator/
│       └── scripts/
│
├── .wolf/
├── .claude/
├── .obsidian/
└── .githooks/
```

| Path | Current purpose |
|---|---|
| `00-home/` | Operating guides and human navigation. |
| `01-project/` | Goals, requirements, constraints, ethics, and stable project context. |
| `02-research/` | Distilled research notes. The initial scaffold remains biased toward the original realtime-AI/video research case. |
| `03-system/` | Architecture, runtime, performance, and deployment notes for technical projects. This is expected to become profile/domain-specific. |
| `04-decisions/` | Decision records, comparisons, and rationale. |
| `05-operations/` | Experiments, benchmarks, roadmaps, and runbooks. |
| `06-sources/` | Intended source catalog/evidence area. Structured canonical source records are not implemented yet. |
| `90-inbox/` | Raw research intake and processing workflow. |
| `99-templates/` | Current Markdown note templates. |
| `skills/.../scripts/` | Current helper scripts for audit, frontmatter, intake, and note creation. |
| `.wolf/` | Current OpenWolf context files. |
| `.claude/` | Claude-specific guidance hook. |
| `.obsidian/` | Obsidian presentation assets. |
| `.githooks/` | Repository-local Git hooks. |

---

# Current manual research intake

The existing implementation supports a manual intake flow.

## 1. Drop

Place a raw artifact in:

```text
90-inbox/raw/
```

The current design treats raw originals as immutable.

## 2. Register

For a local file:

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py \
  --file my-report.pdf \
  --kind pdf \
  --owner curator
```

## 3. Triage

Determine:

- source type;
- relevant research domain;
- canonical URL/identifier;
- publication/update date;
- decision impact;
- whether the material extends, conflicts with, or supersedes existing knowledge.

## 4. Process

Use:

```text
99-templates/intake-record-template.md
```

Capture:

- source metadata;
- summary;
- claims;
- evidence locations;
- configurations or constraints;
- limitations;
- unanswered questions;
- decision impact.

## 5. Distill

Create or update durable research notes.

Current evidence-origin labels:

| Label | Meaning |
|---|---|
| **Observed** | Directly measured or observed in your own work or experiment. |
| **Source-reported** | A source states the claim; it has not necessarily been independently verified. |
| **Inference** | A conclusion derived from evidence or reasoning. |

## 6. Close

Record the outcome and archive the processing record.

The current intake lifecycle and tooling contain known inconsistencies and are not intended to become the final multi-agent state model. See [AUDIT.md](AUDIT.md).

---

# Current helper commands

## Audit

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py
```

## Frontmatter dry run

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py
```

Apply:

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/frontmatter_fix.py --apply
```

## Register intake

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py \
  --file report.pdf \
  --kind pdf \
  --owner curator
```

List:

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py --list
```

## Scaffold a note

The current CLI expects space-separated tags:

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/new_note.py \
  --domain 02-research \
  --title "My Research Topic" \
  --tags ai streaming
```

Do not currently use:

```text
--tags ai,streaming
```

The existing script treats that as one literal tag. This is a known defect scheduled for correction.

---

# Current knowledge-base conventions

Current human-facing guidance lives in:

- [00-home/vault-standards.md](00-home/vault-standards.md)
- [00-home/knowledge-base-guide.md](00-home/knowledge-base-guide.md)
- [00-home/research-intake-guide.md](00-home/research-intake-guide.md)

Current required frontmatter:

```yaml
type: <note-type>
status: <lifecycle-status>
tags:
  - <tag>
```

Current document lifecycle values:

```text
current
draft
stale
superseded
```

The target architecture separates document lifecycle from:

- claim verification;
- freshness;
- decision status;
- source status;
- task status;
- run status.

One global status vocabulary should not be overloaded across all object types.

---

# Planned multi-agent architecture

The following roles are part of the audited target architecture and are **not yet implemented**.

## Orchestrator

Owns:

- research brief;
- research questions;
- coverage matrix;
- research plan;
- task generation;
- bounded delegation;
- stop conditions;
- escalation;
- maintenance requests.

It should coordinate work rather than perform every research action itself.

## Research / discovery agent

Searches one bounded research lane.

Produces:

- candidate sources;
- exact URLs/identifiers;
- search history;
- useful leads;
- dead ends;
- new questions;
- potential source lineage.

It should not turn search snippets directly into trusted knowledge.

## Acquisition agent

Turns a candidate into a canonical source.

Responsibilities:

- retrieval;
- canonical identity;
- metadata normalization;
- content hash;
- version/date capture;
- deduplication;
- raw/snapshot storage handling;
- source record creation.

## Pipeline-processing agent

Converts acquired source material into addressable evidence.

Extracts:

- candidate claims;
- definitions;
- entities;
- relationships;
- measurements;
- dates;
- methods;
- constraints;
- assumptions;
- limitations;
- citations;
- unanswered questions.

Exact source locators must be preserved.

## Classification and linking agent

Maps extracted information into the knowledge model.

Responsibilities:

- evidence-origin classification;
- evidence-role classification;
- source directness;
- entity resolution;
- canonical tag mapping;
- duplicate claim detection;
- conflict detection;
- topic/domain mapping;
- relationship creation.

## Verification / critic agent

Independently checks important claims.

It should test:

- whether the cited source actually supports the statement;
- whether the locator is correct;
- whether date/version/unit/scope are correct;
- whether sources are independent;
- whether contradictory evidence exists;
- whether the claim is fresh enough.

For high-impact claims it should actively look for disconfirming evidence.

## Sorting and cleanup agent

Maintains organization without changing research meaning.

Examples:

- safe link repair;
- generated-index rebuilds;
- duplicate-note proposals;
- file placement checks;
- formatting normalization;
- orphan detection;
- tag alias cleanup;
- stale temporary artifact cleanup.

Destructive or semantic changes should require stronger review.

## Knowledge-maintenance agent

Determines whether maintenance is required and executes the appropriate maintenance class.

It should inspect:

- repository state;
- stale claims;
- changed sources;
- unresolved conflicts;
- duplicate candidates;
- failed tasks;
- expired leases;
- graph/index freshness;
- audit results;
- evaluation regressions.

Maintenance decisions should be based on deterministic thresholds and state, not intuition.

## Knowledge Base Query / Answer agent

This is the primary user-facing agent for asking questions **about the maintained knowledge base**.

Typical interaction:

```text
User:
What did our research conclude about X?

KB Query Agent:
- direct answer;
- supporting claims;
- source citations and exact locators;
- conflicts or caveats;
- freshness/validity information;
- remaining knowledge gaps.
```

### Default behavior

The query agent should be **KB-first and KB-bounded**.

It should search the repository in this order:

1. exact IDs and metadata;
2. canonical entities and aliases;
3. verified claim records;
4. research notes;
5. source/evidence relationships;
6. lexical full-text search;
7. graph-neighborhood expansion;
8. optional semantic retrieval.

It should prefer verified claims and evidence edges over loosely related prose.

### Answer contract

A structured answer should normally contain:

1. **Answer** — concise response to the question.
2. **Evidence** — the claims or findings that establish the answer.
3. **Sources** — canonical source title/ID and exact locator where possible.
4. **Confidence / status** — supported, disputed, stale, unresolved, etc.
5. **Conflicts and caveats** — contradictory or scope-limited evidence.
6. **Freshness** — `valid_as_of`, `last_verified`, or review-due state where relevant.
7. **Knowledge gaps** — what the KB does not currently establish.

Example target response shape:

```text
Answer
The current KB supports <conclusion>.

Evidence
- clm_... — <claim>
- clm_... — <claim>

Sources
- src_... — <title>, section 3.2
- src_... — <title>, p. 14

Status
Supported by two independent sources. Last verified 2026-09-21.

Caveat
A conflicting source reports <difference> for version Y.

Gap
The KB has no verified evidence for version Z.
```

### Strict grounding rule

If the KB does not establish an answer, the agent should say:

> The current knowledge base does not establish this.

It must not silently fill the gap using model memory.

It may:

- identify related material;
- explain exactly what is missing;
- propose a research-gap record;
- request a research task from the orchestrator;
- optionally perform external research only when explicitly requested and permitted by policy.

### Write permissions

The default query agent should be read-oriented.

Safe writes may be limited to:

- query event;
- feedback event;
- proposed research-gap task.

It should not directly rewrite source, claim, decision, or entity records while answering a question.

This separation prevents Q&A behavior from silently changing the knowledge it is querying.

## Synthesis agent

Produces larger human-facing artifacts such as:

- research reports;
- technical comparisons;
- literature reviews;
- design briefs;
- decision-support reports.

Unlike the query agent, the synthesis agent can combine a large set of verified claims into a new long-form artifact.

## Evolution agent

Proposes improvements to:

- ontology;
- aliases;
- search strategy;
- source adapters;
- extraction fields;
- schemas;
- maintenance policy;
- workflow.

High-impact changes should be reviewed and tested before application.

---

# Planned control plane

The target architecture introduces a dedicated machine-readable control plane.

```text
.research/
├── state.json
├── health.json
├── tasks/
├── runs/
├── events/
├── handoffs/
├── maintenance/
├── locks/
└── generated/
```

The design deliberately avoids one large shared mutable JSON document.

Instead:

- one event file records one material action;
- one task file owns one task's state;
- one run directory owns one research run;
- typed handoff records connect roles;
- generated global snapshots summarize authoritative records;
- maintenance state is derived from policy and events.

This reduces merge conflicts and makes state reconstructable.

---

# Planned authoritative vs generated data

| Surface | Intended authority |
|---|---|
| `research.config.yaml` | Authoritative project and research policy. |
| `schemas/` | Authoritative machine contracts. |
| Agent role manifests | Authoritative role capabilities. |
| Source records | Authoritative canonical source metadata. |
| Claim records | Authoritative structured claims. |
| Entity records | Authoritative entity identity/aliases. |
| Task records | Authoritative workflow state. |
| Event records | Authoritative action history. |
| Run records | Authoritative research-run state. |
| `.research/state.json` | Generated snapshot. |
| `.research/health.json` | Generated health state. |
| Graph/search indexes | Generated and rebuildable. |
| Markdown manifests/catalogs | Human projections where possible. |
| Obsidian dashboard | Presentation only. |

Agents should eventually be prevented from editing generated state as if it were source data.

---

# Planned evidence model

The target model keeps several dimensions separate.

## Evidence origin

```text
observed
source_reported
inferred
```

## Evidence role

```text
supports
contradicts
qualifies
contextualizes
updates
supersedes
```

## Evidence directness

```text
primary
secondary
tertiary
unknown
```

A single opaque trust score should not replace these inspectable properties.

---

# Planned claim model

Claims should become first-class records with stable IDs.

Example:

```yaml
id: clm_<stable-id>
statement: ""
claim_type: factual
claim_status: supported
freshness_status: fresh
valid_as_of: 2026-09-21

evidence:
  - source_id: src_<stable-id>
    segment_id: seg_<stable-id>
    role: supports
    origin: source_reported

related_claims:
  - id: clm_<stable-id>
    relation: contradicts
```

Expected claim states include:

```text
candidate
supported
disputed
contradicted
superseded
stale
unresolved
```

This makes questions such as these mechanically answerable:

- Why do we believe this?
- Which evidence supports it?
- Which evidence contradicts it?
- When was it last verified?
- Which notes, reports, or decisions depend on it?
- Is the knowledge still valid?

---

# Planned repository state

A mature project should be resumable without relying on chat history.

State should eventually track:

- active research runs;
- task queue;
- task leases;
- retries and failure classes;
- role/instruction versions;
- source changes;
- claim verification status;
- open gaps;
- unresolved conflicts;
- maintenance counters;
- audit status;
- state/index freshness.

A new agent should be able to determine:

- what already happened;
- what is running;
- what failed;
- what is blocked;
- what work is due;
- what needs verification;
- whether maintenance is necessary;
- which instructions governed previous work.

---

# Planned maintenance model

The system should be able to answer:

> Is maintenance required, what kind, and why?

Maintenance is split into separate classes.

## Structural maintenance

Examples:

- invalid schemas;
- broken references;
- generated-state drift;
- orphan runtime state;
- abandoned tasks;
- migration issues.

## Research maintenance

Examples:

- stale claims;
- changed source versions;
- unresolved critical gaps;
- contradictory evidence;
- superseded evidence.

## Ontology maintenance

Examples:

- duplicate entities;
- tag aliases;
- relation normalization;
- concept merge/split candidates.

## Operational maintenance

Examples:

- stuck leases;
- failed runs;
- stale caches;
- storage cleanup;
- retry exhaustion.

Maintenance triggers should be deterministic and configuration-driven.

---

# Planned state/event model

Material actions should eventually produce immutable structured events.

Example classes:

```text
run.created
run.completed

task.created
task.claimed
task.blocked
task.completed
task.failed

source.discovered
source.acquired
source.changed
source.duplicate_detected

claim.extracted
claim.classified
claim.verified
claim.disputed
claim.stale
claim.superseded

entity.created
entity.alias_added
entity.merge_proposed

gap.created
gap.resolved

maintenance.requested
maintenance.completed

evolution.proposed
evolution.applied

query.asked
query.answered
query.insufficient_evidence
```

The Q&A agent should record enough metadata to make frequently asked questions and recurrent knowledge gaps observable without copying sensitive source content into logs.

---

# Planned source adapters

The engine should remain provider-independent.

Conceptual adapter contract:

```text
discover(query, scope) -> candidate sources
fetch(source_ref) -> raw artifact + metadata
normalize(raw artifact) -> canonical source record
segment(source) -> addressable source segments
refresh(source_id) -> changed | unchanged | unavailable
```

Potential adapters include:

- general web;
- official documentation;
- GitHub;
- academic indexes;
- standards bodies;
- local files;
- datasets;
- transcripts;
- internal company connectors;
- user-provided source lists.

---

# Security and trust boundaries

All external research material should be treated as untrusted input.

A future implementation should enforce:

- source content cannot modify agent policy;
- source content cannot request secrets;
- source text cannot directly grant tool permissions;
- ingestion/parsing agents use minimal permissions;
- executable source artifacts are not automatically executed;
- credentials remain outside the repository;
- suspicious embedded instructions are treated as data and can be logged as source risk;
- sensitive information is governed by explicit classification and storage policy.

The control plane and the research content plane must remain separate.

---

# Target repository architecture

The current tree is expected to evolve toward something closer to:

```text
/
├── README.md
├── AGENTS.md
├── research.config.yaml
├── pyproject.toml
├── CHANGELOG.md
│
├── agents/
│   ├── common.md
│   ├── orchestrator.md
│   ├── research-agent.md
│   ├── acquisition-agent.md
│   ├── pipeline-processing-agent.md
│   ├── classification-agent.md
│   ├── verification-agent.md
│   ├── sorting-cleanup-agent.md
│   ├── knowledge-maintenance-agent.md
│   ├── knowledge-query-agent.md
│   ├── synthesis-agent.md
│   ├── evolution-agent.md
│   └── roles/
│
├── schemas/
├── src/polder_research/
├── tests/
│
├── .research/
│   ├── state.json
│   ├── health.json
│   ├── tasks/
│   ├── runs/
│   ├── events/
│   ├── handoffs/
│   ├── maintenance/
│   ├── locks/
│   └── generated/
│
├── 00-home/
├── 01-project/
├── 02-research/
│   └── domains/
├── 03-knowledge/
│   ├── claims/
│   ├── entities/
│   ├── conflicts/
│   └── gaps/
├── 04-decisions/
├── 05-operations/
│   ├── runs/
│   ├── experiments/
│   ├── benchmarks/
│   ├── maintenance/
│   ├── evaluations/
│   ├── audits/
│   ├── reports/
│   └── runbooks/
├── 06-sources/
│   └── records/
├── 07-evolution/
│   ├── proposals/
│   ├── migrations/
│   └── changelog.md
├── 90-inbox/
└── 99-templates/
```

The exact numbering is less important than preserving clean authority boundaries.

---

# Development order

The detailed roadmap is in [AUDIT.md](AUDIT.md).

The recommended sequence is:

## A. Make current guidance truthful

Fix:

- missing referenced files;
- intake-table bug;
- tag parsing/documentation;
- dashboard async read;
- root frontmatter mismatch;
- committed bytecode;
- hook/bootstrap guidance;
- audit blind spots;
- documentation contract tests.

## B. Establish one schema authority

Add:

- schema registry;
- central vocabularies;
- schema versions;
- migration system;
- generated-vs-authoritative rules.

## C. Establish the control plane

Add:

- project config;
- agent role instructions;
- machine-readable role capabilities;
- tasks;
- runs;
- events;
- handoffs;
- idempotency;
- leases;
- maintenance rules;
- state builder.

## D. Establish evidence primitives

Add:

- source records;
- segments;
- claims;
- evidence edges;
- entities;
- conflicts;
- gaps;
- provenance derivation.

## E. Add KB querying

Implement the Knowledge Base Query / Answer agent only after evidence primitives are reliable.

It should first support:

- exact metadata retrieval;
- claim retrieval;
- source-backed answers;
- conflict/freshness reporting;
- structured citations;
- insufficient-evidence detection.

Semantic retrieval can be added afterward as an accelerator, not as the authority layer.

## F. Enable autonomous research

Then add:

- source discovery adapters;
- acquisition workers;
- processing;
- classification;
- verification;
- synthesis;
- adaptive research loops.

## G. Enable controlled self-evolution

Only after evaluation is stable:

- query-learning;
- ontology proposals;
- automatic low-risk cleanup;
- maintenance automation;
- workflow evolution.

**Autonomy must not outrun auditability.**

---

# Known limitations in the current scaffold

The current repository contains confirmed inconsistencies.

Examples:

- some documented files do not exist;
- the intake lifecycle differs between documentation and code;
- the first intake row can be written outside the intended Queue table;
- the note generator bypasses the canonical template system;
- the documented comma-separated tag example is incompatible with the current CLI;
- Unicode/non-Latin titles are not handled robustly by the current slugger;
- the dashboard contains logic that should eventually move into derived state;
- source and domain counts currently include navigation notes;
- filesystem modification time is used as a freshness proxy;
- archives are partially excluded from integrity checking;
- schema constants are duplicated across scripts;
- the pre-commit hook requires manual activation;
- there is no CI/test suite yet;
- main is currently unprotected.

These are tracked and prioritized in [AUDIT.md](AUDIT.md).

---

# Contributing and architecture changes

Until the control plane and schemas exist:

- keep changes small and explicit;
- run the current audit before committing;
- do not silently change the meaning of evidence labels;
- do not introduce a second competing intake convention;
- do not treat generated dashboard output as authoritative state;
- preserve source URLs and evidence locations;
- record architectural decisions in the audit/decision documentation.

Changes to future control-plane surfaces such as:

- `agents/`;
- `schemas/`;
- `research.config.yaml`;
- migrations;
- source/evidence semantics;

should eventually receive stronger review than ordinary research-note additions.

---

# Key documents

| Document | Purpose |
|---|---|
| [AUDIT.md](AUDIT.md) | Canonical audit and implementation specification: current defects, target architecture, dashboard, agent/state model, security, automation, roadmap, and acceptance gates. |
| [AGENTS.md](AGENTS.md) | Current agent-facing repository guidance. |
| [00-home/knowledge-base-guide.md](00-home/knowledge-base-guide.md) | Current folder and knowledge-base conventions. |
| [00-home/research-intake-guide.md](00-home/research-intake-guide.md) | Current manual intake workflow. |
| [00-home/vault-standards.md](00-home/vault-standards.md) | Current note/frontmatter/link conventions. |
| [index.md](index.md) | Current Obsidian Dataview dashboard. |

---

# License

Private repository. All rights reserved.
