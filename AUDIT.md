---
type: guide
status: current
tags:
  - audit
  - architecture
  - research-pipeline
  - governance
---

# Polder Research Pipeline — Canonical Audit

Audit date: 2026-09-21  
Canonical audit file: `AUDIT.md`  
Repository: `PolderLabs/polder-research-pipeline`

This is the single canonical audit and improvement specification for Polder Research Pipeline. It consolidates the earlier append-only audit, removes superseded recommendations, resolves duplicated priorities, and defines one current target architecture.

The repository should be understood as a **versioned research data model and agent control plane with Markdown/Obsidian as a human-facing projection**.

The long-term goal is a reusable research operating system that can start from an arbitrary project, question, investigation, technical subject, literature review, product study, policy topic, or other research domain and then:

- plan research;
- discover and acquire sources;
- process heterogeneous material;
- extract claims, entities, measurements, dates, relationships, limitations, and open questions;
- classify and link evidence;
- verify important claims;
- maintain durable knowledge;
- answer questions from the knowledge base with exact source provenance;
- track agent actions and repository state;
- detect stale, changed, conflicting, duplicated, or unsupported knowledge;
- trigger maintenance deterministically;
- evolve its ontology and workflow through controlled, auditable changes.

---

# 1. Audit-of-the-audit

The previous audit file was useful for exploration but had become unsuitable as an implementation contract.

## 1.1 Problems found in the previous audit

The previous file was approximately 185k characters with more than 400 headings. It was built by appending new audit rounds instead of revising old conclusions.

This caused:

- multiple repository structures, some explicitly marked “revised”;
- multiple implementation phase plans;
- multiple acceptance-gate sections;
- multiple overlapping P0/P1 backlogs;
- dashboard findings repeated at several levels;
- agent-state recommendations repeated with slightly different terminology;
- earlier recommendations remaining visible after later sections superseded them;
- excessive heading depth;
- a reader needing to know which later section overrides which earlier section;
- audit history and canonical specification being mixed together.

## 1.2 Resolution

This file uses these rules:

1. One finding appears once in its canonical section.
2. Later thinking is incorporated directly instead of appended as a competing recommendation.
3. “Current implementation” and “target architecture” are explicitly separated.
4. Priority is defined once.
5. Acceptance criteria are defined once.
6. Terminology is canonicalized.
7. Dashboard, security, automation, agent roles, state, and knowledge modeling are integrated into the same architecture.
8. Historical audit narration is omitted unless it materially explains a design decision.
9. External references are collected in one section.
10. Future audits should edit this file in place rather than append another full audit pass.

---

# 2. Executive assessment

## 2.1 What is good in the current scaffold

The current repository already contains useful foundations:

- clear numbered content domains;
- a raw intake concept;
- Markdown/YAML conventions;
- note templates;
- an Obsidian dashboard;
- link/frontmatter/tag/orphan audit tooling;
- intake and note helper scripts;
- a local pre-commit hook;
- evidence-origin terminology;
- conflict-note concept;
- decision and experiment templates;
- human-readable project structure.

These are useful primitives.

## 2.2 What is missing

The repository is not yet the research pipeline it describes.

The major missing capabilities are:

- generic research project initialization;
- research briefs;
- adaptive research planning;
- source discovery adapters;
- canonical source records;
- content hashing;
- deduplication;
- source segmentation;
- claim records;
- evidence edges;
- entity resolution;
- exact provenance;
- verifier workflow;
- task/run/event state;
- typed handoffs;
- maintenance engine;
- change-impact propagation;
- knowledge-query agent;
- CI/tests/schema registry;
- autonomous agent permission boundaries;
- controlled self-evolution.

## 2.3 Main architectural decision

The strongest architecture is not:

> an Obsidian vault that agents edit.

It is:

> a versioned research data/control system in which Markdown and Obsidian are one human interface.

That distinction is central because workflow state, freshness, source identity, task state, provenance, and agent permissions should not be inferred from display files.

---

# 3. Current repository defects

The items below are confirmed defects or contract mismatches in the current scaffold.

## 3.1 Missing documented files

Current guidance references files that do not exist, including:

- `skills/obsidian-knowledgebase-curator/SKILL.md`;
- `skills/obsidian-knowledgebase-curator/README.md`;
- `99-templates/research-note-template.md`;
- `06-sources/reference-catalog.md`;
- `.wolf/cerebrum.md`;
- `.wolf/anatomy.md`.

These are P0 because they make documented operating paths false.

## 3.2 Source/research template confusion

`99-templates/source-entry-template.md` is structurally a research note, not a canonical source-record template.

Fix:

- create `research-note-template.md`;
- create a true `source-record-template.md`;
- register template type -> schema -> generator mapping;
- fail audit when template filename, frontmatter type, and schema disagree.

## 3.3 Intake lifecycle disagreement

Documentation and `intake_register.py` define different states.

The system needs one machine-readable state machine.

Recommended intake flow:

`new -> triaged -> acquiring -> processing -> extracted -> verified -> distilled -> filed`

Additional states:

- `blocked`;
- `rejected`.

Transitions must be validated.

## 3.4 Source-kind disagreement

Documentation and code use different vocabularies.

Separate:

`source_type`:
- paper;
- documentation;
- repository;
- webpage;
- article;
- dataset;
- benchmark;
- video;
- audio;
- transcript;
- book;
- standard;
- issue;
- discussion;
- other.

`media_type`:
- pdf;
- html;
- markdown;
- text;
- json;
- csv;
- image;
- audio;
- video;
- git;
- api;
- other.

## 3.5 Intake tags are accepted but not stored

`intake_register.py --tags` currently accepts values without persisting them.

Fix or remove the option.

## 3.6 First intake row placement bug

When the queue contains no existing data rows, the first row can be appended after the explanatory sections rather than inside the Queue table.

This is a correctness bug.

## 3.7 Manifest updates use substring matching

Item updates can match a filename occurring anywhere in a row.

Use stable intake IDs and exact record identity.

## 3.8 Duplicate intake is not prevented

Canonical deduplication should consider, in order:

1. DOI/standard identifier;
2. repository URL + commit/tag;
3. canonical URL;
4. SHA-256;
5. normalized title + author/date;
6. semantic near-duplicate detection.

## 3.9 Markdown table state is unsafe for concurrent agents

A single Markdown table should not be authoritative multi-agent workflow state.

Use one structured record per item. Generate the Markdown manifest as a human view.

## 3.10 Table injection risk

Unescaped pipe characters in manifest fields can corrupt the table.

Structured records remove this issue.

## 3.11 Raw source immutability is not verifiable

Raw ignored files can be modified or disappear.

Register:

- content hash;
- byte size;
- MIME;
- original filename;
- source URI;
- retrieval timestamp;
- storage pointer.

## 3.12 Raw-file ignore policy is overly broad

Root `.gitignore` ignores several binary extensions globally.

Prefer path-scoped storage rules under raw storage instead of blocking legitimate artifacts anywhere in the repo.

## 3.13 Frontmatter root-type inconsistency

Current standards say `index` is for `index.md` and `moc` for domain README files, but root files do not consistently follow that contract.

Use path-aware schemas.

## 3.14 Frontmatter parser is a partial YAML implementation

Either:

- formally support a strict subset; or
- use a proper YAML parser and validate with schemas.

Do not claim arbitrary YAML compatibility if unsupported.

## 3.15 Frontmatter fixer overstates its behavior

It says it normalizes values but primarily fills missing fields.

Rename or implement safe normalization with dry-run diffs.

## 3.16 Future skill corruption risk

`vault_audit.py` excludes `skills/`, while `frontmatter_fix.py` does not share exactly the same scan universe.

Adding SKILL.md could cause a vault frontmatter fixer to mutate a skill file.

All tools must use one registry of content-plane/control-plane scan scopes.

## 3.17 Archive excluded from integrity validation

Archived intake records remain provenance.

They may be excluded from orphan rules but not from schema/link/ID validation.

## 3.18 Hard-coded developer path

Repository-relative instructions are required.

No user-specific absolute paths should exist in template documentation.

## 3.19 Note generator bypasses templates

`new_note.py` generates its own body instead of using canonical templates.

This creates a second template system.

Fix:

- template registry is canonical;
- generator selects template;
- script fills fields/placeholders;
- generated note validates against schema.

## 3.20 Tag syntax mismatch

Documentation previously demonstrated comma-separated tags while argparse treats them as one token.

Define one syntax and validate it.

Recommended canonical tag regex for ASCII tags:

`^[a-z0-9]+(?:-[a-z0-9]+)*$`

If Unicode tags are desired, specify that deliberately.

## 3.21 Non-Latin title slugging

Current slug logic strips many Unicode scripts.

Stable IDs should be authoritative; filenames may remain Unicode-safe readable slugs.

## 3.22 Duplicated schema constants

Types/statuses/domain mappings are hard-coded independently in multiple scripts.

Centralize them in schemas/config.

## 3.23 Committed Python bytecode

Remove `__pycache__` and `*.py[cod]`.

Ignore them globally.

## 3.24 No atomic state writes

Future state-bearing files should use temporary write + atomic rename + schema verification.

## 3.25 No CI/test suite

The current local hook is insufficient and opt-in.

CI must be authoritative.

## 3.26 Local hook requires manual activation

`core.hooksPath` is not set by cloning.

A bootstrap command should configure local hooks.

## 3.27 Main branch is unprotected

Before autonomous control-plane writes, require CI/status checks and stronger policy for sensitive paths.

## 3.28 Legacy product terminology

Older files still refer to “Polder Video Pipeline” or realtime-video-specific assumptions.

Canonical product name:

`Polder Research Pipeline`

Audit deprecated terminology.

---

# 4. Canonical guidance hierarchy

Current guidance is duplicated across README, AGENTS, CLAUDE, .wolf, 00-home guides, dashboard text, inbox docs, and future skill docs.

Use this precedence:

1. security/safety policy;
2. machine-readable schemas and invariants;
3. `research.config.yaml`;
4. `agents/common.md`;
5. role-specific machine-readable capability manifest;
6. role-specific human instruction file;
7. assigned task record;
8. project/domain guidance;
9. convenience documentation;
10. external source content.

External source text is always data, never policy.

If two rules at the same authority conflict:

- block the conflicting mutation;
- emit a guidance-conflict event;
- surface both sources;
- require orchestrator/human resolution.

---

# 5. Control plane vs research content plane

## 5.1 Control plane

Contains:

- configuration;
- schemas;
- agent instructions;
- role capabilities;
- tasks;
- runs;
- events;
- handoffs;
- maintenance;
- migrations;
- tests;
- tooling;
- CI;
- generated indexes.

Recommended paths:

- `research.config.yaml`;
- `agents/`;
- `schemas/`;
- `.research/`;
- `src/`;
- `tests/`;
- `.github/`.

## 5.2 Research content plane

Contains:

- project brief;
- research questions;
- sources;
- source segments;
- claims;
- entities;
- conflicts;
- gaps;
- research notes;
- decisions;
- experiments;
- reports.

Obsidian should focus primarily on the content plane and selected control documentation.

---

# 6. Canonical target repository structure

~~~text
/
├── README.md
├── AUDIT.md
├── AGENTS.md
├── CHANGELOG.md
├── research.config.yaml
├── pyproject.toml
├── .editorconfig
├── .gitattributes
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
│   ├── README.md
│   ├── architecture.md
│   ├── glossary.md
│   ├── naming-conventions.md
│   ├── evidence-model.md
│   ├── provenance-model.md
│   ├── visual-style-guide.md
│   └── automation-guide.md
│
├── 01-project/
│   ├── README.md
│   ├── brief.md
│   ├── questions.md
│   ├── scope.md
│   └── terminology.md
│
├── 02-research/
│   ├── README.md
│   └── domains/
│       └── <profile-defined-domain>/
│
├── 03-knowledge/
│   ├── claims/
│   ├── entities/
│   ├── conflicts/
│   └── gaps/
│
├── 04-decisions/
│
├── 05-operations/
│   ├── runs/
│   ├── experiments/
│   ├── benchmarks/
│   ├── maintenance/
│   ├── evaluations/
│   ├── audits/
│   ├── reports/
│   └── runbooks/
│
├── 06-sources/
│   └── records/
│
├── 07-evolution/
│   ├── proposals/
│   ├── migrations/
│   └── changelog.md
│
├── 90-inbox/
└── 99-templates/
~~~

`03-system` should become a profile-defined technical research domain rather than a universal kernel folder.

---

# 7. Naming and repository conventions

## 7.1 Canonical names

Product: `Polder Research Pipeline`  
Short name: `PRP`  
Python package: `polder_research`  
CLI: `research`

## 7.2 File naming

- conventional root files: `README.md`, `AGENTS.md`, `AUDIT.md`, `CHANGELOG.md`;
- human notes: lowercase kebab-case;
- Python modules: snake_case;
- role docs: `<role>-agent.md`;
- role manifests: `agents/roles/<role>-agent.yaml`;
- schemas: `<record>.schema.json`;
- templates: `<record>-template.md`;
- audit reports: `YYYY-MM-DD--audit--<slug>.md`.

## 7.3 Stable IDs

Recommended prefixes:

- run: `run_`;
- task: `task_`;
- event: `evt_`;
- source: `src_`;
- segment: `seg_`;
- claim: `clm_`;
- entity: `ent_`;
- question: `qst_`;
- gap: `gap_`;
- conflict: `cnf_`;
- decision: `dec_`;
- experiment: `exp_`;
- benchmark: `bnch_`;
- maintenance: `mnt_`;
- evolution: `evo_`;
- handoff: `hnd_`;
- note: `note_`.

Use UUIDv7 for new durable IDs.

Do not encode mutable title/status/folder/agent identity in IDs.

## 7.4 Data naming

JSON/YAML keys: snake_case.

Use typed status fields:

- `lifecycle_status`;
- `claim_status`;
- `verification_status`;
- `freshness_status`;
- `decision_status`;
- `task_status`;
- `run_status`;
- `source_status`;
- `maintenance_status`.

## 7.5 Timestamp rules

Machine timestamps: RFC 3339 UTC, e.g. `2026-09-21T21:42:14Z`.

- `*_at` = timestamp;
- `*_date` = date only;
- durations include units, e.g. `duration_ms`.

## 7.6 Event grammar

`<object>.<past-tense-event>`

Examples:

- `source.acquired`;
- `claim.verified`;
- `task.completed`;
- `query.answered`;
- `maintenance.completed`.

## 7.7 Git conventions

Branches:

- `feat/<slug>`;
- `fix/<slug>`;
- `docs/<slug>`;
- `refactor/<slug>`;
- `research/<slug>`;
- `maintenance/<slug>`.

Commits use Conventional Commits style.

Releases use SemVer once a public template/CLI contract exists.

---

# 8. Generic project configuration

Add `research.config.yaml`.

Example:

~~~yaml
schema_version: 1

template:
  name: polder-research-pipeline
  version: 0.1.0

project:
  initialized: true
  id: example-project
  title: Example Research Project
  description: ""
  language: en
  initialized_at: 2026-09-21T21:42:14Z

research:
  objective: ""
  depth: standard
  stop_conditions:
    minimum_independent_sources: 3
    maximum_open_critical_gaps: 0

source_policy:
  prefer_primary_sources: true
  prefer_official_sources: true
  allowed_domains: []
  blocked_domains: []
  social_sources: contextual-only
  archive_mutable_web_sources: true

agents:
  max_parallel_workers: 5
  require_verifier_for_current_notes: true
  require_citations_for_factual_claims: true

maintenance:
  incremental_interval_days: 7
  full_interval_days: 30
  max_actions_before_incremental: 100
  max_source_changes_before_incremental: 25
  max_unresolved_duplicates: 10
  max_unresolved_critical_conflicts: 5

knowledge:
  stable_ids: true
  claim_records: true
  entity_resolution: true
  contradiction_detection: true
  semantic_index: optional

profile:
  name: generic
~~~

Profiles may seed domain structure and vocabulary but must not alter provenance semantics.

Suggested profiles:

- generic;
- software/technology;
- scientific/literature-review;
- security;
- product/market;
- hardware/engineering;
- policy/regulatory.

---

# 9. Research brief

Research starts from a brief, not from a file drop.

Required brief fields:

- main research question;
- intended decision/deliverable;
- scope;
- out-of-scope;
- target audience;
- geography;
- time scope;
- freshness requirement;
- depth;
- known facts;
- assumptions;
- terminology;
- preferred source types;
- prohibited sources;
- tool/budget constraints;
- privacy/licensing constraints;
- output format;
- completion criteria.

The orchestrator converts this into questions and a coverage matrix.

---

# 10. Canonical research pipeline

The pipeline is iterative.

~~~text
brief
→ plan
→ discover
→ acquire
→ normalize/deduplicate
→ parse/segment
→ extract
→ classify/link
→ verify/challenge
→ distill
→ synthesize/query
→ maintain
→ revise plan when gaps remain
~~~

## 10.1 Plan

Create:

- primary questions;
- subquestions;
- research lanes;
- expected evidence;
- source strategies;
- completion criteria.

Coverage matrix:

| Question | Priority | Evidence needed | Status | Sources | Verification | Gaps |
|---|---:|---|---|---:|---|---|

## 10.2 Discover

Discovery workers search bounded lanes.

Potential adapters:

- web;
- official documentation;
- GitHub;
- academic indexes;
- standards organizations;
- local files;
- datasets;
- transcripts;
- internal connectors;
- user lists.

Discovery results are candidate sources, not evidence yet.

## 10.3 Acquire

Record:

- canonical URL;
- retrieval time;
- publication/update time;
- author/publisher;
- version/commit/DOI;
- MIME/media type;
- content hash;
- storage pointer;
- licensing/sensitivity.

## 10.4 Normalize/deduplicate

Use canonical identifiers and hashes before semantic similarity.

Preserve mirrors/alternate URLs as aliases.

## 10.5 Parse/segment

Each segment stores:

- source ID;
- segment ID;
- locator;
- content hash;
- parser version.

## 10.6 Extract

Extract:

- claims;
- entities;
- definitions;
- measurements;
- dates;
- methods;
- constraints;
- assumptions;
- limitations;
- relationships;
- unanswered questions.

## 10.7 Classify/link

Evidence origin:

- observed;
- source_reported;
- inferred.

Evidence role:

- supports;
- contradicts;
- qualifies;
- contextualizes;
- updates;
- supersedes.

Evidence directness:

- primary;
- secondary;
- tertiary;
- unknown.

## 10.8 Verify

Check:

- source actually supports claim;
- locator;
- version/date/unit;
- scope;
- source independence;
- primary evidence where appropriate;
- contradicting evidence;
- freshness.

High-impact claims should receive disconfirming searches.

## 10.9 Distill

Durable research notes summarize verified structured knowledge and link claim/source IDs.

## 10.10 Query/synthesize

Answers and reports must trace:

`answer/report -> claim -> evidence edge -> source segment -> source`.

## 10.11 Maintain

Refresh based on source change, freshness policy, conflicts, gaps, and maintenance thresholds.

---

# 11. Source model

One canonical record per source.

Recommended fields:

~~~yaml
id: src_<uuidv7>
schema_version: 1
source_status: current
source_type: documentation
media_type: html
title: ""
authors: []
publisher: ""
canonical_url: ""
alternate_urls: []
doi: ""
repository: ""
version: ""
commit: ""
published_at: ""
updated_at: ""
retrieved_at: ""
last_checked_at: ""
language: en
license: ""
content_sha256: ""
raw_location: ""
archive_location: ""
independence_group: ""
sensitivity: public
storage_policy: metadata-only
tags: []
entities: []
research_runs: []
~~~

Track source lineage:

- cites;
- mirrors;
- republishes;
- summarizes;
- forks;
- derives_from;
- vendor_claim_about;
- independent_replication_of.

Do not count derivative reporting as independent corroboration.

---

# 12. Segment and citation model

Citation locator examples:

- PDF: page + section;
- webpage: heading + snapshot hash;
- video/audio: timestamp;
- repository: commit + file + line range;
- standard: clause;
- dataset: version + selection/filter;
- API: endpoint + retrieval time.

A semantic/vector chunk is not an authoritative citation unless it resolves to the underlying source segment.

---

# 13. Claim model

Example:

~~~yaml
id: clm_<uuidv7>
schema_version: 1
statement: ""
claim_type: factual
claim_status: supported
freshness_status: fresh
importance: medium
scope:
  time: ""
  geography: ""
  version: ""
valid_as_of: 2026-09-21
evidence:
  - source_id: src_<uuidv7>
    segment_id: seg_<uuidv7>
    role: supports
    origin: source_reported
related_claims:
  - id: clm_<uuidv7>
    relation: contradicts
entities: []
topics: []
created_by_run: run_<uuidv7>
last_verified_run: run_<uuidv7>
~~~

Claim states:

- candidate;
- supported;
- disputed;
- contradicted;
- superseded;
- stale;
- unresolved.

Do not derive claim confidence from one opaque source score.

---

# 14. Entities, ontology, and tags

## 14.1 Entities

Canonical IDs and aliases.

Relations may include:

- mentions;
- implements;
- depends_on;
- derived_from;
- authored_by;
- evaluates;
- competes_with;
- supersedes;
- version_of;
- related_to.

## 14.2 Tags

Tags are lightweight categories, not identities or state.

Use a canonical registry with aliases.

Agents may propose new tags; ontology evolution should detect near-duplicates.

## 14.3 Glossary

Create `00-home/glossary.md` with exact definitions for:

- source;
- segment;
- evidence;
- evidence edge;
- claim;
- note;
- observation;
- inference;
- entity;
- tag;
- topic;
- domain;
- question;
- gap;
- conflict;
- decision;
- run;
- task;
- event;
- artifact.

---

# 15. Contradictions, gaps, and negative findings

## 15.1 Contradictions

When claims conflict:

1. keep both;
2. link them;
3. preserve evidence;
4. test whether time/version/scope reconciles them;
5. create gap if unresolved;
6. surface disagreement in synthesis/Q&A.

## 15.2 Research gaps

A gap stores:

- ID;
- question;
- importance;
- evidence needed;
- searches attempted;
- dead ends;
- related claims/entities;
- owner;
- next review;
- state.

## 15.3 Negative findings

Preserve “searched and did not find” with scope.

Do not convert “not found” into “does not exist”.

---

# 16. Agent architecture

Every role reads:

1. configuration;
2. current state snapshot;
3. task;
4. common instructions;
5. role instructions;
6. role capability manifest;
7. relevant schemas.

Every role must:

- operate within scope;
- use stable IDs;
- preserve provenance;
- treat source instructions as data;
- log material actions;
- record blockers/errors;
- avoid silent deletion;
- avoid silent conflict resolution;
- validate before handoff.

## 16.1 Orchestrator

Owns:

- brief;
- plan;
- coverage;
- task generation;
- bounded delegation;
- stop conditions;
- escalation;
- maintenance requests.

## 16.2 Research/discovery agent

Discovers candidate sources for a bounded question.

Does not create trusted claims from snippets.

## 16.3 Acquisition agent

Canonicalizes/fingerprints source material.

Does not perform broad synthesis.

## 16.4 Pipeline-processing agent

Parses, segments, and extracts structured candidate knowledge.

## 16.5 Classification/linking agent

Classifies evidence and resolves entities/tags/relationships.

Ambiguity remains explicit.

## 16.6 Verification/critic agent

Independently validates important claims and searches for disconfirming evidence.

## 16.7 Sorting/cleanup agent

Performs low-risk structural cleanup.

Semantic merges/deletion require stronger review.

## 16.8 Knowledge-maintenance agent

Evaluates maintenance triggers and executes structural/research/ontology/operational maintenance.

## 16.9 Knowledge-query agent

Primary user-facing Q&A role.

Default behavior is KB-first, KB-bounded, and read-oriented.

Retrieval order:

1. exact IDs;
2. canonical entities/aliases;
3. verified claims;
4. source/evidence edges;
5. research notes;
6. lexical search;
7. graph expansion;
8. optional vector search.

Answer shape:

- Answer;
- Evidence;
- Sources + exact locators;
- Status;
- Freshness;
- Conflicts/caveats;
- Knowledge gaps.

If the KB cannot establish the answer:

> The current knowledge base does not establish this.

The agent may propose a research-gap task but must not silently use model memory as evidence.

Default writes:

- query event;
- answer event;
- feedback event;
- proposed gap/task.

It must not directly mutate verified claims, entities, source records, decisions, schemas, or policy while answering.

## 16.10 Synthesis agent

Creates larger evidence-backed reports.

## 16.11 Evolution agent

Proposes ontology/query/workflow/schema improvements.

High-impact evolution requires tests and review.

---

# 17. Machine-readable role manifests

Each role has a YAML manifest specifying:

- instruction version;
- task types;
- readable paths;
- writable paths;
- forbidden paths;
- tools;
- network policy;
- external browsing;
- code execution;
- destructive permissions;
- approval requirements.

Example:

~~~yaml
schema_version: 1
role: knowledge-query-agent
instruction_version: 1

task_types:
  - query.answer
  - query.explain
  - query.compare
  - query.trace-source

read:
  - 01-project/**
  - 02-research/**
  - 03-knowledge/**
  - 04-decisions/**
  - 05-operations/reports/**
  - 06-sources/**
  - .research/generated/**
  - .research/state.json

write:
  - .research/events/**
  - .research/handoffs/**
  - .research/tasks/**

forbidden:
  - research.config.yaml
  - schemas/**
  - agents/**
  - 03-knowledge/claims/**
  - 03-knowledge/entities/**
  - 04-decisions/**
  - 06-sources/records/**
~~~

Runtime enforcement is preferred over prompt-only enforcement.

---

# 18. State model

Use event-sourced small records, not one shared mutable ledger.

~~~text
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
~~~

Authoritative:

- event files;
- task files;
- run files;
- handoffs;
- source/claim/entity/gap/decision records.

Derived:

- state.json;
- health.json;
- action log;
- graph/indexes;
- human manifests/catalogs.

Derived state must be rebuildable.

---

# 19. Events

Event record should include:

- event ID;
- timestamp;
- agent/actor;
- role;
- instruction version;
- config/schema versions;
- code revision;
- run/task IDs;
- action;
- inputs;
- targets;
- summary;
- result;
- artifacts;
- sanitized errors;
- metadata.

Important event families:

- run.*;
- task.*;
- source.*;
- segment.*;
- claim.*;
- entity.*;
- gap.*;
- conflict.*;
- maintenance.*;
- evolution.*;
- audit.*;
- query.*.

One event per file avoids append conflicts.

---

# 20. Task model

Task fields:

- task ID;
- run ID;
- role;
- objective;
- priority;
- task status;
- dependencies;
- inputs;
- allowed outputs;
- acceptance checks;
- idempotency key;
- attempt;
- max attempts;
- failure class;
- lease;
- heartbeat;
- expected input revision;
- output schema version;
- budget;
- timestamps.

States:

- queued;
- claimed;
- running;
- blocked;
- completed;
- failed;
- cancelled.

Use leases and expiry for recovery.

---

# 21. Handoffs

Typed handoffs:

- discovery_to_acquisition;
- acquisition_to_processing;
- processing_to_classification;
- classification_to_verification;
- verification_to_distillation;
- maintenance_to_research;
- evolution_to_migration.

Handoffs must be schema-valid before the receiver begins.

---

# 22. Run model

Run states:

- planned;
- active;
- paused;
- blocked;
- completed;
- failed;
- cancelled.

Record:

- brief revision;
- execution envelope;
- phase;
- tasks;
- budgets;
- stop conditions;
- blockers;
- generated artifacts;
- stop reason.

Runs should resume rather than restart when safe.

---

# 23. State freshness and concurrency

Derived snapshots include:

- generated_at;
- source_commit;
- last_event_id;
- event_count;
- generator_version;
- schema_version.

State is stale when any of these no longer match authoritative data.

Workers should not rebuild global snapshots after every event.

Use:

- per-record writes;
- phase-boundary rebuilds;
- maintenance rebuilds;
- CI drift checks.

Semantic records use optimistic concurrency with expected revision/hash.

---

# 24. Reliability and failure handling

## 24.1 Error taxonomy

- transient;
- validation;
- policy;
- permission;
- conflict;
- dependency;
- source-unavailable;
- source-malformed;
- budget;
- timeout;
- rate-limit;
- internal;
- unknown.

## 24.2 Retry

Retry only retryable classes with bounded attempts/backoff.

Never retry indefinitely.

## 24.3 Circuit breakers

Repeated adapter/parser/provider failure should mark that dependency degraded and pause new assignments.

## 24.4 Budgets

Per-task limits may include:

- tool calls;
- source count;
- wall time;
- cost.

Stop reason must be explicit.

## 24.5 Idempotency

Examples:

- acquisition keyed by URL + retrieval-policy version;
- processing by source + hash + parser version;
- classification by segment-set hash + schema version;
- verification by claim revision + policy version.

Reuse equivalent completed work.

## 24.6 Tombstones

Do not erase provenance-bearing identity.

Use supersession/redirect/tombstone semantics.

---

# 25. Maintenance architecture

Maintenance is separated into four classes.

## 25.1 Structural

- schemas;
- broken references;
- generated drift;
- migrations;
- invalid records;
- abandoned tasks.

## 25.2 Research

- stale claims;
- changed sources;
- unresolved conflicts;
- open critical gaps;
- superseded evidence.

## 25.3 Ontology

- duplicate entities;
- tag aliases;
- relation normalization;
- concept split/merge proposals.

## 25.4 Operational

- failed runs;
- expired leases;
- retries;
- stale caches;
- storage cleanup.

Maintenance triggers are deterministic.

Example rule record:

~~~json
{
  "rule": "stale_high_impact_claims",
  "value": 4,
  "threshold": 1,
  "severity": "high",
  "triggered": true,
  "maintenance_class": "research"
}
~~~

Scheduled automation should create tasks/reports/PRs rather than silently rewrite trusted conclusions.

---

# 26. Controlled self-evolution

Loop:

`Observe -> Propose -> Evaluate -> Apply -> Record -> Re-evaluate`

System may learn:

- aliases;
- useful query expansions;
- high-value source locations;
- source adapters;
- recurring tags/concepts;
- unresolved gaps;
- duplicate patterns;
- successful report structures;
- failed search patterns.

Safe low-risk automation:

- generated index rebuild;
- alias suggestions;
- stale flags;
- source refresh scheduling;
- backlink repair where unambiguous.

Review required:

- schema changes;
- destructive merges;
- knowledge deletion;
- accepted-decision changes;
- evidence-model changes;
- source-policy changes;
- privacy/security changes;
- disputed-claim resolution.

---

# 27. Provenance

Model entities, activities, and agents.

Every trusted artifact should answer:

- what produced it?
- from which inputs?
- during which run?
- using which code/config/instruction versions?
- which model/tool/runtime?
- when?
- what superseded it?

Event logs describe what happened.

Provenance relationships describe derivation.

Both are required.

---

# 28. Freshness model

Filesystem mtime is not knowledge freshness.

Use:

- updated_at;
- reviewed_at;
- review_after;
- source_checked_at;
- valid_as_of;
- freshness_status.

Freshness policy depends on volatility.

Examples:

- pricing: short;
- security advisories: very short;
- software releases: moderate;
- peer-reviewed paper: longer;
- pinned standard version: event-triggered;
- historical fact: usually stable.

No universal 90-day stale rule.

---

# 29. Experiments and benchmarks

Experiments should capture:

- ID;
- hypothesis/claim IDs;
- environment fingerprint;
- hardware/software versions;
- container/image hash;
- random seed;
- dataset version/hash;
- input artifact IDs;
- command/config;
- raw result pointers;
- metric definition version;
- abort conditions;
- repeats;
- analysis version;
- observed vs inferred result.

Benchmarks need their own template/schema.

---

# 30. Decision records

Decision records should include:

- decision ID;
- decision status;
- owner;
- accepted_at;
- claim IDs;
- source IDs where direct;
- assumptions;
- review triggers;
- supersession;
- uncertainty;
- affected constraints.

If a critical supporting claim changes, the decision should become review-due.

---

# 31. Storage, privacy, and sensitivity

Sensitivity levels:

- public;
- internal;
- confidential;
- restricted.

Storage modes:

- metadata only;
- Git;
- Git LFS;
- local-only;
- object storage;
- external canonical source.

Source record should capture:

- storage policy;
- redistribution rights;
- sensitivity;
- personal-data flag.

Restricted material must not be sent to external model providers unless policy permits it.

Logs must not blindly store:

- source text;
- credentials;
- authorization headers;
- connector tokens;
- personal data;
- confidential prompts.

---

# 32. Ingestion security

All external content is untrusted.

## 32.1 Network policy

Default fetcher:

- HTTP/HTTPS only;
- block loopback;
- block link-local;
- block private ranges unless explicitly allowed;
- limit redirects;
- revalidate redirect targets;
- timeouts;
- byte limits;
- MIME sniffing.

## 32.2 Quarantine

Before parsing check:

- size;
- MIME;
- extension mismatch;
- archive depth;
- compression ratio;
- path traversal;
- symlinks;
- executables;
- macros;
- encryption;
- malformed input;
- content hash.

## 32.3 Parser isolation

Where practical:

- low privilege;
- no credentials;
- no unnecessary network;
- read-only input;
- CPU/memory/time limits;
- controlled output.

Do not execute scripts/macros/notebooks/binaries/build systems merely to understand source content.

## 32.4 Prompt injection

Source instructions are data.

They cannot:

- change role policy;
- grant permissions;
- request secrets;
- authorize writes;
- override safety or control-plane instructions.

---

# 33. Knowledge-query quality gates

Before returning a sourced answer:

1. claim exists;
2. claim revision is current;
3. evidence edge resolves;
4. segment/source resolves;
5. locator exists;
6. claim is not silently superseded;
7. freshness is known;
8. conflicts are surfaced;
9. answer wording does not exceed claim scope.

Track:

- unsupported_claim_rate;
- incorrect_citation_rate;
- citation_locator_accuracy;
- conflict_omission_rate;
- stale_evidence_use_rate;
- scope_overreach_rate;
- insufficient_evidence_detection_rate.

---

# 34. Dashboard audit

The dashboard should be the primary human control surface, not a repository showcase.

Its first questions should be:

1. What project is this?
2. Is the system healthy?
3. What needs attention?
4. What changed?
5. What remains unresolved?
6. What can I do next?
7. Where is the evidence?

## 34.1 Current dashboard correctness defects

Current metrics can appear authoritative while using invalid proxies.

Confirmed problems:

- source count includes the sources README/MOC;
- domain counts include MOCs;
- “research gaps” are draft notes;
- “stale” uses file mtime;
- recent decisions are based on mtime, not decision status;
- raw inbox counts do not reliably represent ignored binaries;
- inbox age uses file mtime;
- recent activity means file modification;
- last updated means any vault modification;
- manifest read is asynchronous but used synchronously;
- operator links include nonexistent files;
- editable project title is browser-local.

Fix data semantics before visual polish.

## 34.2 Target dashboard hierarchy

~~~text
HEADER
Project title · health · state refresh

ASK THE KNOWLEDGE BASE
search/ask surface

ATTENTION
critical issues requiring action

RESEARCH COVERAGE     ACTIVE WORK
questions/gaps        run/tasks/blockers

RECENT VERIFIED       SOURCE HEALTH
semantic changes      changed/missing/new

DECISIONS & IMPACT    MAINTENANCE
review due            audit/refresh due

RESEARCH AREAS
compact navigation

ADMIN & TOOLS
collapsed by default
~~~

## 34.3 Current scaffold dashboard

Until structured state exists, only display truthful current data.

Use:

- compact header;
- quick navigation;
- actual audit/frontmatter/orphan issues;
- durable research-note activity;
- intake status only after registry correctness is fixed;
- compact domains;
- tools/admin links.

Do not simulate claim health, coverage, or maintenance intelligence before their authoritative state exists.

## 34.4 Ask vs Search

Search finds a note/entity/claim/source/ID.

Ask produces a grounded answer.

These should be distinct modes.

## 34.5 Attention center

Priority:

1. critical audit/provenance failure;
2. failed/stuck task;
3. changed source affecting accepted decision;
4. disputed high-impact claim;
5. stale high-impact claim;
6. unresolved critical conflict;
7. verification backlog;
8. overdue maintenance;
9. intake backlog;
10. cleanup.

Each item shows:

- severity;
- object;
- reason;
- age;
- action.

## 34.6 Replace vanity metrics

Demote/remove:

- total domains;
- total notes;
- top tags as primary KPI.

Prefer:

- needs attention;
- open gaps;
- disputed claims;
- verification queue;
- changed sources;
- active work.

Every metric should drill down to underlying records.

## 34.7 Semantic activity

Future Recent Activity should use event records, not mtime.

Events:

- source acquired/changed;
- claim verified/disputed;
- gap resolved;
- decision accepted;
- maintenance completed;
- run completed.

## 34.8 Domain navigation

Keep compact and secondary.

Domain color may aid navigation but must not imply status.

## 34.9 Admin surfaces

Templates, operator docs, skills, audit tooling, and internal navigation belong under a collapsed Admin & Tools section.

---

# 35. Dashboard visual system

Desired direction:

- neutral;
- professional;
- information-led;
- low ornament;
- theme-native;
- compact;
- action-oriented.

Reduce:

- oversized hero;
- decorative greetings/emojis;
- glassmorphism;
- blur;
- glow;
- excessive shadows;
- many separate rounded cards;
- remote fonts;
- tiny uppercase labels.

## 35.1 Component namespace

Use `prp-`.

Examples:

- `.prp-dashboard`;
- `.prp-header`;
- `.prp-panel`;
- `.prp-status`;
- `.prp-alert`;
- `.prp-list-row`;
- `.prp-button`;
- `.prp-chip`.

Avoid global `.span-4` style utilities.

## 35.2 Design tokens

Use tokens:

- `--prp-color-bg-*`;
- `--prp-color-text-*`;
- `--prp-color-border-*`;
- `--prp-color-accent`;
- `--prp-color-status-success`;
- `--prp-color-status-info`;
- `--prp-color-status-pending`;
- `--prp-color-status-warning`;
- `--prp-color-status-danger`;
- `--prp-color-status-neutral`;
- `--prp-space-*`;
- `--prp-radius-*`.

## 35.3 Semantic status meanings

- success = verified/supported/healthy/completed;
- info = current/active/informational;
- pending = queued/draft/proposed;
- warning = stale/review-due/degraded;
- danger = failed/contradicted/rejected/critical;
- neutral = superseded/archived/inactive/unknown.

Color must not be the sole state cue.

## 35.4 Light/dark

Explicitly test light and dark themes.

Prefer Obsidian semantic variables where possible.

## 35.5 Typography

Suggested:

- page title 24–28px;
- section 13–14px/600;
- metric 24–32px;
- body 14–16px;
- metadata 12–13px.

Prefer native/interface fonts.

Remote Google Fonts should be optional, not required.

## 35.6 Radius/spacing

Radius:

- 6px;
- 8px;
- 12px;
- pill only for chips.

Spacing:

- 4;
- 8;
- 12;
- 16;
- 24;
- 32.

## 35.7 Motion

No `transition: all`.

Respect `prefers-reduced-motion`.

## 35.8 Accessibility

Baseline:

- WCAG 2.2 AA;
- normal text >= 4.5:1;
- large text >= 3:1;
- meaningful UI/focus contrast >= 3:1;
- color not sole meaning;
- visible `:focus-visible`;
- suitable target size;
- semantic HTML where possible;
- no hover-only critical info.

## 35.9 Responsive behavior

Wide:
- max width ~1280–1400;
- two-column major panels.

Tablet:
- panels stack or 6/6;
- metrics 2x2.

Narrow:
- single column;
- no fixed labels;
- no large hero;
- no horizontal scrolling.

Obsidian pane width matters more than application-window width; use container-aware behavior where practical.

---

# 36. Dashboard data authority

| Dashboard data | Authority |
|---|---|
| project title | research.config.yaml |
| active run | run/state records |
| tasks | task records |
| gaps | gap records |
| disputed claims | claim records |
| stale claims | freshness engine |
| source changes | source records/events |
| maintenance due | maintenance state |
| audit health | health.json |
| semantic activity | event log |
| intake backlog | structured intake records |
| source count | source records |
| decision review | decisions + impact graph |

Dataview should render state, not define its semantics.

---

# 37. Obsidian architecture

Core mode must work without Obsidian.

Core:

- filesystem;
- Markdown;
- YAML/JSON;
- Git;
- CLI;
- CI.

Obsidian enhancement:

- dashboard;
- graph browsing;
- Dataview;
- CSS;
- human navigation.

Do not make Dataview authoritative.

Long-term data flow:

`authoritative records -> state builders -> state/health JSON -> dashboard projection`.

---

# 38. Automation and engineering standards

## 38.1 Local fast checks

- Ruff;
- JSON/YAML/schema validation;
- frontmatter;
- naming;
- deprecated terminology;
- internal links;
- cache/bytecode;
- secrets;
- generated-file protection.

## 38.2 Pull-request CI

- unit tests;
- schema tests;
- full repository audit;
- docs conformance;
- full links;
- state/event integrity;
- generated drift;
- fixtures;
- control-plane policy.

## 38.3 Scheduled health

Weekly:

- external link report;
- dependency health;
- maintenance triggers;
- stale state;
- source refresh candidates;
- orphan leases/tasks;
- ontology drift.

Scheduled jobs should not silently rewrite trusted research conclusions.

## 38.4 Full maintenance

Monthly/manual:

- all fixtures;
- graph/index rebuild;
- source consistency;
- ontology analysis;
- archive integrity;
- evaluation history.

## 38.5 Release

- full CI;
- migration tests;
- changelog/version checks;
- deterministic build;
- release notes.

---

# 39. Python/tooling standards

Add `pyproject.toml`.

Use:

- Ruff;
- pytest;
- proper YAML parser;
- JSON Schema validator;
- type checker if complexity warrants it.

Move reusable implementation from skill scripts into `src/polder_research/`.

Skills become wrappers/instructions over core functionality.

Declare supported Python versions and lock dependencies deterministically.

---

# 40. Schema registry

Use one schema dialect, preferably JSON Schema Draft 2020-12.

Schemas:

- project-config;
- role;
- event;
- task;
- run;
- handoff;
- source;
- segment;
- claim;
- entity;
- gap;
- conflict;
- decision;
- experiment;
- benchmark;
- maintenance;
- evolution.

Every record has `schema_version`.

Migrations are explicit and tested.

---

# 41. Testing

## 41.1 Unit tests

All core modules.

## 41.2 Conformance fixtures

At minimum:

- valid-minimal-project;
- broken-guidance-reference;
- first-intake-item;
- duplicate-source;
- conflicting-claims;
- stale-high-impact-claim;
- expired-task-lease;
- source-version-change;
- non-latin-title;
- malformed-tag;
- missing-provenance;
- schema-migration;
- exact-answer;
- unsupported-question;
- conflicting-answer-evidence;
- version-mismatch;
- source-lineage.

## 41.3 Documentation contract tests

Test:

- file paths;
- CLI examples;
- template names;
- enum values;
- operator surfaces.

Documentation is part of the product contract.

## 41.4 Generated drift

Run generators and require clean Git diff.

---

# 42. GitHub repository governance

Before broad autonomous writing:

- CI required on main;
- protect main where supported;
- block force push/deletion;
- require stronger review for control-plane changes;
- add CODEOWNERS for:
  - agents;
  - schemas;
  - research.config.yaml;
  - src;
  - .github;
  - evolution/migrations.

GitHub Actions:

- minimum permissions;
- third-party actions pinned to full SHAs;
- concurrency cancellation for stale PR runs.

Dependabot:

- Python;
- GitHub Actions.

---

# 43. Audit severity model

## Error — blocks merge/trusted handoff

- schema invalid;
- authoritative reference broken;
- provenance missing;
- illegal transition;
- generated drift;
- secret detected;
- test failure;
- control-plane conflict;
- unauthorized role write.

## Warning

- external link unavailable;
- review due;
- near-duplicate ontology item;
- noncritical stale claim;
- maintenance threshold near.

## Info

- refresh suggestion;
- cleanup candidate;
- performance advisory.

---

# 44. Source-of-truth matrix

| Surface | Authority | Rebuildable |
|---|---|---:|
| research.config.yaml | authoritative policy | no |
| schemas/* | authoritative contracts | no |
| role manifests | authoritative capabilities | no |
| source records | authoritative source metadata | no |
| claim records | authoritative structured knowledge | no |
| entity records | authoritative identity | no |
| task records | authoritative workflow state | no |
| events | authoritative history | no |
| run records | authoritative run state | no |
| state.json | derived snapshot | yes |
| health.json | derived snapshot | yes |
| graph/index | derived | yes |
| manifest.md | human projection | yes |
| source catalog | human projection | yes |
| vector index | derived | yes |
| dashboard | presentation | yes |

Agents should never manually edit derived files as if they were authority.

---

# 45. Priority roadmap

This is the single canonical implementation order.

## P0 — make current repository truthful

- fix missing referenced files;
- fix first intake row;
- fix manifest exact identity;
- fix tag behavior;
- fix dashboard async read;
- fix root frontmatter contracts;
- remove hard-coded local path;
- remove bytecode;
- remove legacy naming;
- fix hook/bootstrap guidance;
- make audit include control/operator paths;
- test existing documented commands.

Exit criterion:

> Every currently documented path/command works as documented, and the repository cannot report clean when an operating path is broken.

## P1 — conventions and schema authority

- naming conventions;
- glossary;
- stable IDs;
- timestamp rules;
- typed statuses;
- schema registry;
- migrations;
- template registry;
- .editorconfig;
- .gitattributes;
- path-scoped storage ignores.

Exit criterion:

> No important vocabulary/state rule is independently hard-coded in multiple tools.

## P2 — control plane

- research.config.yaml;
- common agent contract;
- role docs;
- role manifests;
- event records;
- task records;
- run records;
- typed handoffs;
- leases;
- idempotency;
- state builder;
- health builder;
- maintenance rules.

Exit criterion:

> A new agent can determine what it may do, what has been done, what is pending, what is blocked, and which state is authoritative.

## P3 — CI and security foundation

- pyproject;
- deterministic dependencies;
- Ruff/pytest;
- docs tests;
- fixtures;
- GitHub CI;
- generated drift;
- secret scanning;
- minimum workflow permissions;
- parser quarantine/sandbox;
- network/SSRF policy;
- sensitivity routing.

Exit criterion:

> Autonomous output cannot enter trusted state without deterministic validation and permission checks.

## P4 — evidence primitives

- source records;
- source deduplication;
- segments;
- exact locators;
- claims;
- evidence edges;
- entities;
- aliases;
- conflicts;
- gaps;
- provenance graph;
- freshness;
- source lineage;
- impact analysis.

Exit criterion:

> Every trusted claim can answer “why do we believe this, from exactly where, under which version/scope?”

## P5 — dashboard rebuild

First implement a truthful scaffold dashboard.

Then, after structured state exists:

- Ask KB;
- attention queue;
- research coverage;
- active work;
- semantic activity;
- source health;
- decision impact;
- maintenance state.

Exit criterion:

> Dashboard values come only from documented authoritative state and prioritize what needs attention.

## P6 — knowledge-query agent

- exact retrieval;
- lexical retrieval;
- graph expansion;
- optional vector layer;
- provenance validation;
- stale/conflict warnings;
- gap creation;
- feedback loop.

Exit criterion:

> It answers only what the KB establishes and cites exact evidence.

## P7 — autonomous research workers

- discovery adapters;
- acquisition;
- processing;
- classification;
- verification;
- distillation;
- synthesis;
- bounded orchestrator loops;
- budgets/retries/circuit breakers.

Exit criterion:

> A complete research brief can execute end-to-end with resumable, auditable state.

## P8 — maintenance and self-evolution

- scheduled health;
- source refresh;
- query-learning;
- ontology proposals;
- evolution proposals;
- safe auto-apply classes;
- evaluation history.

Exit criterion:

> Repeated use improves the system without silent changes to authoritative meaning.

---

# 46. Acceptance criteria

## 46.1 Guidance

- one precedence model;
- no broken operator references;
- no deprecated terminology;
- docs examples tested;
- role/instruction versions recorded.

## 46.2 Structure

- control and content planes separated;
- template and project lifecycle separated;
- profile-specific domains not hard-coded into kernel;
- generated files rebuildable;
- archived provenance still valid.

## 46.3 Conventions

- filenames conform;
- IDs conform;
- timestamps conform;
- event grammar conforms;
- status fields typed;
- templates match schemas.

## 46.4 State

- tasks idempotent;
- leases expire/recover;
- retries traceable;
- events immutable;
- snapshots advertise freshness;
- handoffs typed;
- execution envelope recorded.

## 46.5 Research quality

- claims have provenance;
- important claims verified;
- conflicts visible;
- source independence modeled;
- gaps first-class;
- negative findings scoped;
- freshness policy-driven.

## 46.6 Security

- role permissions enforceable;
- model output schema-validated;
- source content cannot alter policy;
- fetching protects internal networks;
- parsing is sandboxed/quarantined;
- sensitive data obeys routing/logging policy;
- secrets blocked.

## 46.7 Dashboard

- no semantically false metric;
- zero vs unknown distinguishable;
- first viewport shows attention/current work;
- metrics drill down;
- admin content secondary;
- semantic colors;
- light/dark;
- reduced motion;
- visible focus;
- responsive narrow layout;
- no mandatory external fonts.

## 46.8 Automation

- fresh clone bootstrap deterministic;
- PR CI complete;
- generated drift blocks;
- schemas tested;
- dependencies locked;
- workflows least-privilege;
- third-party actions SHA-pinned;
- scheduled jobs do not silently rewrite research.

## 46.9 Reusability

- works for non-software topics;
- Obsidian optional;
- Unicode titles safe;
- storage configurable;
- sensitivity configurable;
- upgrades use migrations.

---

# 47. Immediate implementation batch

The first implementation batch should be deliberately small and foundational:

1. add canonical naming/glossary docs;
2. fix all currently broken references;
3. create the missing curator skill/readme or remove references;
4. split research-note and source-record templates;
5. fix intake first-row/update/tag bugs;
6. fix dashboard async read and remove misleading metrics;
7. remove committed bytecode and tighten ignores;
8. add .editorconfig/.gitattributes;
9. centralize schema constants;
10. add pyproject + tests;
11. add CI;
12. only after that start building .research state.

Do not begin broad autonomous research before this batch is stable.

---

# 48. References

Architecture/provenance:

- W3C PROV Primer: https://www.w3.org/TR/prov-primer/
- RFC 9562 UUIDs: https://www.rfc-editor.org/rfc/rfc9562.html
- JSON Schema: https://json-schema.org/specification

Agent/research architecture:

- Anthropic multi-agent research system: https://www.anthropic.com/engineering/multi-agent-research-system
- OpenAI Deep Research system card: https://openai.com/index/deep-research-system-card/
- Microsoft GraphRAG: https://www.microsoft.com/en-us/research/project/graphrag/
- OpenAI Agents SDK concepts: https://openai.github.io/openai-agents-python/

Accessibility/UI:

- WCAG 2.2 Use of Color: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color
- WCAG contrast: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum
- WCAG focus appearance: https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance
- WCAG reduced motion technique: https://www.w3.org/WAI/WCAG22/Techniques/css/C39

Engineering/governance:

- GitHub Actions secure use: https://docs.github.com/en/actions/reference/security/secure-use
- GitHub workflow syntax/concurrency: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub protected branches: https://docs.github.com/en/repositories/configuring-branches-and-merges/managing-protected-branches/about-protected-branches
- GitHub Dependabot for Actions: https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/auto-update-actions
- Conventional Commits: https://www.conventionalcommits.org/en/v1.0.0/
- Semantic Versioning: https://semver.org/

---

# 49. Audit maintenance rules

This file is itself part of the repository contract.

Future audits must follow these rules:

1. Edit canonical sections in place.
2. Do not append a second competing architecture.
3. Do not add “revised roadmap” sections; update the roadmap.
4. Do not create duplicate backlogs.
5. Mark findings as fixed by changing their state in the canonical section or removing them from the current-defect list after verification.
6. Record audit date and inspected commit at the top when materially re-audited.
7. Keep current-state facts separate from target-state design.
8. If a recommendation changes, replace the old recommendation rather than preserving contradictory guidance.
9. Keep external references consolidated.
10. Audit this file for duplicate headings, stale filenames, broken internal references, and contradictory state vocabularies as part of CI.

The audit should remain a usable implementation contract, not a chronological transcript of every audit pass.
