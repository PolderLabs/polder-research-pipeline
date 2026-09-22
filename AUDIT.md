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

Audit date: 2026-09-22  
Inspected repository revision: `a309f7d8db443fa423fa12ca69bfdeb738984840`  
Canonical audit file: `AUDIT.md`  
Repository: `PolderLabs/polder-research-pipeline`

This is the single canonical audit and improvement specification for Polder Research Pipeline. It supersedes the former `IMPROVEMENTS.md`, consolidates the earlier append-only audit, removes superseded recommendations, resolves duplicated priorities, and defines one current target architecture.

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


# 0. Implementation status — eight-round re-audit (2026-09-22)

This status replaces the earlier implementation snapshot. It is based on direct inspection of `main` at `a309f7d8db443fa423fa12ca69bfdeb738984840`, the current repository tree, schemas, agent contracts, Python implementation, dashboard, CI configuration, and the actual GitHub Actions result for that revision.

The repository has advanced substantially since the original scaffold, but the foundation is **not yet at the exit criteria previously claimed for P0–P4**.

## 0.1 What is genuinely implemented

- A packaged Python control-plane foundation under `src/polder_research/`.
- Canonical JSON Schemas for tasks, runs, events, handoffs, sources, segments, claims, evidence edges, entities, gaps, conflicts, decisions, and frontmatter.
- Agent role documentation and YAML capability manifests for 11 roles.
- Event, task, run, handoff, state, health, maintenance, source, segment, claim, entity, gap, conflict, and evidence-edge modules.
- Canonical source registration during local-file intake with SHA-256-based duplicate detection.
- `research.config.yaml`, `.editorconfig`, `.gitattributes`, `pyproject.toml`, Ruff configuration, CODEOWNERS, Dependabot, CI, and Gitleaks configuration.
- Previously missing curator/OpenWolf/template/source-catalog files now exist.
- Several original P0 defects were fixed: first intake row placement, exact filename matching, hard-coded local raw path, tracked bytecode, and broader vault-audit coverage.

## 0.2 Current validation state

The canonical audit previously stated that pytest, Ruff, vault audit, schema validation, and secret scanning were clean. That is no longer a valid statement for the inspected revision.

GitHub Actions run:

`https://github.com/PolderLabs/polder-research-pipeline/actions/runs/35717236745`

on `a309f7d8db443fa423fa12ca69bfdeb738984840` completed with **failure**.

Confirmed failed jobs:

- Test (pytest);
- Lint (Ruff);
- Vault audit;
- Schema validation and generated drift;
- Secret scan (Gitleaks).

Dependabot configuration checks succeeded.

The connector exposed job conclusions but not usable job logs, so this audit distinguishes **confirmed red CI** from **inferred root causes**. The source-level defects below independently justify the failed-readiness assessment.

## 0.3 Roadmap status after re-audit

### P0 — partially complete

Many original scaffold defects are fixed, but the exit gate is not met because CI is red, dashboard correctness defects remain, status documentation overstates validation, intake still uses filename/table identity, and some writers emit records that violate canonical schemas.

### P1 — partially complete

Conventions, schemas, a glossary, and registries now exist, but important vocabulary is still duplicated across `research.config.yaml`, JSON Schemas, `polder_research.paths`, and intake/new-note scripts.

### P2 — structurally present, reliability incomplete

Tasks, runs, events, handoffs, state, health, and maintenance exist, but idempotency, lease safety, atomic writes, concurrency, execution-envelope provenance, runtime capability enforcement, and durable authoritative-state persistence remain incomplete.

### P3 — CI/security scaffolding present, exit gate not met

CI/security configuration exists, but CI is red, Python metadata conflicts with runtime code, dependencies are not fully locked, runtime ingestion security controls are missing, and main remains unprotected.

### P4 — evidence primitives present, correctness incomplete

Source, segment, claim, entity, gap, conflict, and evidence-edge primitives exist, but writer/schema mismatches, referential-integrity gaps, and incomplete evidence tests remain.

### P5–P8

Still pending in the intended sense: state-driven professional dashboard/research planning, executable knowledge-query agent, bounded autonomous research workers, and controlled maintenance/self-evolution.

## 0.4 Immediate stabilization principle

Do not add broader autonomy until:

1. every authoritative writer produces schema-valid records;
2. authoritative records are durably persisted and recoverable;
3. GitHub CI is green on the declared supported runtime.

The next implementation batch should be stabilization work, not feature expansion.

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

## 1.3 Self-audit result

The consolidated audit was itself checked after restructuring. The canonical file now has one target repository structure, one priority roadmap, one acceptance-criteria section, one dashboard specification, and one source-of-truth model. Normalized heading names are unique, there are no references to the former `IMPROVEMENTS.md` inside this audit, and historical recommendations that conflict with the current architecture were removed rather than retained as competing guidance.

The remaining mention of the old product name `Polder Video Pipeline` is intentional: it appears only as a confirmed legacy-terminology defect that must be removed from the repository.

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

# 3. Current repository defects after the eight-round re-audit

This section replaces the original scaffold-defect inventory. Fixed original findings are listed at the end as regression requirements rather than open defects.

## 3.1 CI is red while audit/README claim validation is clean — critical

The latest inspected `main` commit has failing GitHub Actions jobs for pytest, Ruff, vault audit, schema/drift validation, and Gitleaks. Status documentation currently overstates validation.

Required: restore green CI and derive release/readiness claims from current integration evidence.

## 3.2 Declared Python support conflicts with implementation — critical

`pyproject.toml` declares Python `>=3.11` and CI uses 3.12, while core modules call `uuid.uuid7()` directly. Standard-library `uuid.uuid7()` is a Python 3.14 addition.

Choose one explicit contract:

- support 3.11–3.13 through a compatible UUIDv7 implementation; or
- raise the supported Python floor to 3.14.

Test the declared range in CI.

## 3.3 Authoritative state is ignored as if it were derived — critical

The audit and agent contract define events, tasks, runs, handoffs, sources, claims, entities, segments, gaps, conflicts, and evidence edges as authoritative. Current `.gitignore` ignores all of those records and labels the runtime control plane derived/rebuildable.

Only snapshots/indexes/caches and ephemeral locks are inherently rebuildable.

Resolve explicitly with either:

- repository-backed authoritative records tracked by Git; or
- a configured durable external authoritative backend.

Do not leave authoritative state local-only without a persistence contract.

## 3.4 Record writers and canonical schemas disagree — critical

Confirmed examples:

- `register_segment()` writes `created_at`, but `segment.schema.json` forbids that property.
- `acquire_lease()` writes `lease.id`, while the task schema expects fields such as `lease_token` and does not allow `id`.
- `register_gap()` defaults to `priority="moderate"`, while the gap schema allows `low|medium|high|critical`.
- `register_source()` can persist an empty `content_sha256`, while the source schema requires 64 lowercase hex characters.

Every authoritative writer must validate the complete record against the canonical schema before the write succeeds.

## 3.5 Validation happens too late

State readers detect malformed records, but writers do not consistently prevent them.

Required write path:

`construct -> schema validate -> semantic/reference validate -> permission/concurrency validate -> atomic write -> event`

## 3.6 Writes are non-atomic and lack optimistic concurrency

Core modules use direct `write_text()` without expected-revision checks.

Implement atomic replace and revision/hash based optimistic concurrency for mutable authoritative records.

## 3.7 Lease semantics do not prevent collisions

`acquire_lease()` does not reject an existing unexpired lease. Heartbeat, token-checked release, expiry reclamation, lock cleanup, and atomic compare-and-set are missing.

## 3.8 Task idempotency is promised but not enforced

The common contract says every task has an idempotency key, but the schema makes it optional and `write_task()` does not require/generate one or reuse equivalent completed work.

## 3.9 Execution-envelope provenance is placeholder data

Events hard-code `instruction_version: "0.1.0"` and `code_revision: "HEAD"`.

Record exact instruction/manifest/config/schema/code/runtime/model/toolset identity where relevant.

## 3.10 Event contract conflicts with common agent instructions

The common contract requires `tool.called` and `tool.failed`, but the event schema does not allow them. It also documents timestamp/actor/type filenames while code writes `evt_<uuidv7>.json`.

Docs, schema, and implementation must agree.

## 3.11 Error taxonomy is narrower than the canonical reliability model

Unify event/config/code taxonomy for transient, validation, policy, permission, conflict, dependency, source-unavailable, source-malformed, budget, timeout, rate-limit, internal, and unknown errors.

## 3.12 Agent capability manifests are not runtime-enforced

Role YAML manifests exist, but no runtime authorization layer was found for tool calls, path writes, network access, code execution, or destructive actions.

## 3.13 Role responsibilities and permissions conflict

Examples:

- Orchestrator and research-agent both claim end-to-end coordination.
- Acquisition promises raw storage but lacks raw-store write scope.
- Classification assigns evidence relations but cannot write `.research/edges/**`.
- Verification cannot read evidence edges.
- Knowledge-query cannot read evidence edges despite requiring exact provenance.
- Synthesis lacks edge/segment reads despite promising full provenance.
- Evolution reads nonexistent `.research/schemas/**` instead of root `schemas/**`.
- Sorting/cleanup advertises safe fixes but its manifest largely permits reporting only.

Add cross-contract tests for docs, manifests, tools, schemas, and runtime enforcement.

## 3.14 Common agent bootstrap rule is incomplete

“No agent operates outside a task” conflicts with the orchestrator creating the first task/run. Define a bootstrap/admin operation or initial orchestration task.

## 3.15 Evidence relationships have two competing authorities

Both standalone evidence-edge records and embedded `claim.evidence[]` represent the same relationship data.

Use one authority. Recommended: standalone evidence edges are authoritative; claim views reference or derive them.

## 3.16 Referential integrity is incomplete

Generic writers do not consistently prove referenced sources/claims/entities exist. Segment, claim, conflict, and other reference-bearing writers need endpoint validation.

## 3.17 Evidence writers do not universally schema-validate

Source/segment/claim/entity/gap/conflict writers should round-trip through canonical schemas before persistence, as should evidence edges.

## 3.18 Evidence-edge tests contain uncollected nested tests

Several intended tests in `tests/test_evidence_edge.py` are indented inside the `inbox` fixture after its `return`, so pytest does not collect them normally.

Fix structure and assert these test cases are collected.

## 3.19 Source deduplication is fragile around malformed records

`find_duplicate_source()` directly JSON-loads source files. One malformed source can break lookup. Reuse validated-record loading and later normalize DOI/URL identity.

## 3.20 Intake still duplicates vocabularies and lacks stable intake identity

The intake script hard-codes statuses/kinds/source mappings. Manifest identity is filename-based. Stable intake IDs, source IDs in projection, table escaping, structured intake records, concurrency safety, and atomic writes remain missing.

## 3.21 New-note implementation still bypasses canonical authorities

The new-note script hard-codes domain/type/status vocabularies, uses ASCII-only slugging, and constructs note content directly instead of rendering through `TemplateRegistry`.

## 3.22 Maintenance implementation is narrower than its contract

Current evaluation is a useful start, but:

- code references thresholds absent from config;
- superseded sources are used as a duplicate proxy;
- no general freshness engine computes stale state;
- research triggers map poorly to structural passes;
- maintenance classes are not represented explicitly;
- health omits several research/repository signals.

## 3.23 Dashboard P0 correctness defects remain

Current `index.md` still uses asynchronous `app.vault.read()` synchronously, treats drafts as gaps, mtime as knowledge freshness, localStorage as project-title authority, and source-folder page count as source count.

## 3.24 Dashboard visual/accessibility debt remains

Current CSS still uses remote fonts, `transition: all`, lacks `:focus-visible` and reduced-motion handling, retains legacy product naming, and keeps the older decorative layout.

## 3.25 Security foundation is incomplete

CI/security scaffolding exists, but network/SSRF controls, ingestion quarantine, archive safety, parser sandboxing, sensitivity-aware routing, and robust sensitive-log redaction are not implemented.

## 3.26 Gitleaks job is currently failing

The Gitleaks GitHub Actions job fails. The workflow references `GITLEAKS_LICENSE`; exact failure cause was not available through the connector and must be confirmed in Actions logs before changing the gate.

## 3.27 Dependency reproducibility is incomplete

No full dependency lock is committed. CI performs floating operations including pip upgrade and a broad Ruff install in the lint job.

## 3.28 Generated drift check is mostly a placeholder

The CI step does not run a canonical generator and can no-op when `.research/generated` is absent/ignored.

## 3.29 Main remains unprotected

CODEOWNERS exists, but `main` is currently unprotected. Required checks/review policy are not enforced.

## 3.30 Repository metadata remains domain-specific

The GitHub repository description still says it is for realtime AI-driven visual platform research, conflicting with the generic template goal.

## 3.31 Guidance conflicts about source authority

`.wolf/anatomy.md` calls `06-sources/reference-catalog.md` canonical, while the source-of-truth model makes structured source records authoritative and the catalog a human projection.

## 3.32 Fresh clones cannot assume state.json exists

Startup guidance says to read `.research/state.json`, but that derived file may not exist. Rebuild/validate it first when missing or stale.

## 3.33 Audit and README overstate completion

Earlier status claims are inconsistent with current CI and source inspection. Treat readiness/status as a verifiable release claim.

## 3.34 Fixed original defects

These original findings are now resolved or materially improved and should be regression-tested rather than listed as open:

- missing curator SKILL/README;
- missing research-note template;
- missing reference catalog;
- missing OpenWolf anatomy/cerebrum;
- hard-coded raw-directory developer path;
- tracked Python bytecode;
- first intake row placement;
- exact filename matching;
- broader YAML frontmatter parsing;
- basic CI/Dependabot/CODEOWNERS scaffolding.

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

Canonical prefixes:

- run: `run_`;
- task: `tsk_`;
- event: `evt_`;
- source: `src_`;
- segment: `seg_`;
- claim: `clm_`;
- evidence edge: `evd_`;
- entity: `ent_`;
- question: `qst_`;
- gap: `gap_`;
- conflict: `cfl_`;
- decision: `dec_`;
- experiment: `exp_`;
- benchmark: `bnch_`;
- maintenance: `mnt_`;
- evolution: `evo_`;
- handoff: `hnd_`;
- note: `note_`.

The three-letter task/conflict prefixes match the current structured-record implementation and are now canonical.

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

This is the single canonical implementation order after the eight-round re-audit.

## P0 — stabilize the implemented foundation

- restore all GitHub Actions jobs to green;
- make declared Python support match the UUID implementation;
- fix every writer/schema mismatch;
- enforce schema validation before every authoritative write;
- repair uncollected evidence-edge tests;
- define durable persistence for authoritative `.research` records;
- fix remaining dashboard P0 correctness defects;
- correct audit/README completion claims;
- keep fixed original defects covered by regression tests.

Exit criterion:

> Current `main` is green in CI, every public writer round-trips through its canonical schema, and authoritative records survive/reconstruct correctly under the documented persistence model.

## P1 — finish authority and contract unification

- derive/configure shared enums from one authority rather than duplicating them;
- make config, schemas, paths, scripts, docs, and tests agree;
- make TemplateRegistry the actual note-generator authority;
- make Unicode-safe note identity/filenames;
- make evidence edges the single authoritative evidence relation;
- align event types, filenames, error taxonomy, and agent instructions;
- add schema/config contract tests for every duplicated vocabulary.

Exit criterion:

> A concept such as task status, source type, evidence relation, event type, or template type has one canonical definition and all other surfaces consume or validate against it.

## P2 — make the control plane concurrency-safe and enforceable

- require/derive task idempotency keys;
- enforce legal task/run/handoff transitions;
- implement collision-safe leases, heartbeat, expiry, and reclamation;
- use atomic writes;
- add record revisions and optimistic concurrency;
- implement typed handoffs;
- record exact execution envelope;
- enforce role manifests at runtime;
- fix role read/write/tool scopes;
- define orchestration bootstrap semantics;
- build/rebuild stale snapshots deterministically.

Exit criterion:

> Multiple agents can operate concurrently without silent overwrite, duplicate side effects, or unauthorized mutation, and every state transition is attributable and recoverable.

## P3 — finish CI, security, and repository governance

- deterministic dependency locking;
- supported Python-version CI matrix;
- green secret scanning in the organization repository;
- real generated-artifact drift generation/check;
- branch protection/ruleset for main where supported;
- network/SSRF policy before remote source adapters;
- ingestion quarantine and archive safety;
- parser sandbox/resource limits;
- sensitivity-aware provider routing;
- secret/sensitive-log redaction.

Exit criterion:

> Autonomous output cannot enter trusted state without deterministic validation, permission checks, and the security controls relevant to the enabled capabilities.

## P4 — complete evidence integrity and source intelligence

- enforce referential integrity for all writers;
- source canonicalization and resilient deduplication;
- source/segment/claim/evidence graph consistency;
- entity aliases and duplicate resolution;
- freshness engine;
- source lineage;
- changed-source impact propagation;
- automated contradiction candidates;
- decision impact;
- source adapters after security controls exist.

Exit criterion:

> Every trusted claim can answer “why do we believe this, from exactly where, under which version/scope, and what changes if the source changes?”

## P5 — rebuild the dashboard on structured state

Implement a truthful scaffold dashboard first, then add Ask/Search, attention queue, research coverage, active work, semantic activity, source health, decision impact, and maintenance health.

Exit criterion:

> Dashboard values come only from documented authoritative/derived state, distinguish zero/unknown/error, and prioritize what needs attention.

## P6 — implement the executable knowledge-query agent

Implement exact/entity retrieval, lexical retrieval, graph/evidence expansion, optional vector acceleration, provenance validation, stale/conflict/scope warnings, gap/task proposal, feedback, and runtime role enforcement.

Exit criterion:

> It answers only what the KB establishes, cites exact evidence, and explicitly reports insufficient or conflicting knowledge.

## P7 — implement bounded autonomous research workers

Implement secure discovery adapters, acquisition, parsing, classification, verification, distillation, synthesis, adaptive planning, budgets/retries/circuit breakers, and resumable runs/handoffs.

Exit criterion:

> A complete research brief executes end-to-end with bounded, resumable, auditable state and no bypass around evidence/provenance rules.

## P8 — maintenance and controlled self-evolution

Implement scheduled health reporting, source refresh, query-learning, ontology/evolution proposals, safe low-risk auto-apply classes, migration/evaluation history, rollback, and review gates.

Exit criterion:

> Repeated use improves organization and research coverage without silently changing authoritative meaning or policy.

---

# 46. Acceptance criteria

## 46.1 Current foundation

- latest `main` CI is green;
- supported Python versions are explicit and tested;
- public writers emit schema-valid records;
- invalid records cannot enter authority through normal APIs;
- authoritative persistence is documented and durable;
- no status documentation claims a clean state when CI is red.

## 46.2 Guidance

- one precedence model;
- no broken operator references;
- no deprecated product terminology outside explicit history;
- documentation examples tested;
- role/instruction versions recorded;
- agent docs, manifests, schemas, and runtime behavior agree.

## 46.3 Structure

- control and content planes separated;
- template/project lifecycle separated;
- profile-specific domains are not long-term kernel assumptions;
- generated files rebuildable;
- authoritative records not mislabeled as generated;
- archived provenance resolvable.

## 46.4 Conventions

- filenames and canonical prefixes conform;
- timestamps/event grammar conform;
- status fields typed;
- templates match schemas;
- config/schema vocabularies do not drift.

## 46.5 State and concurrency

- tasks idempotent;
- leases collision-safe and recoverable;
- retries traceable;
- writes atomic;
- revisions/concurrency checked;
- snapshots advertise freshness;
- handoffs typed;
- exact execution envelope recorded.

## 46.6 Research quality

- claims have exact provenance;
- evidence relations have one authority;
- references resolve;
- important claims verified;
- conflicts visible;
- source independence modeled;
- gaps first-class;
- freshness policy-driven;
- source changes propagate to dependent knowledge.

## 46.7 Security

- role permissions runtime-enforced;
- model output schema-validated;
- source content cannot alter policy;
- fetching protects internal networks;
- parsing sandboxed/quarantined when enabled;
- sensitive data obeys routing/logging policy;
- secret scanning green;
- control-plane changes governed.

## 46.8 Dashboard

- no semantically false metric;
- zero vs unknown/unavailable/error distinguishable;
- async reads correct;
- project identity comes from shared config;
- first viewport shows attention/current work;
- metrics drill down;
- semantic colors, light/dark, reduced motion, visible focus, responsive layout;
- no mandatory external fonts.

## 46.9 Automation

- fresh clone bootstrap deterministic;
- PR/main CI complete;
- generated drift check actually regenerates/checks tracked derived artifacts;
- schema/meta-contract tests exist;
- dependencies reproducible;
- workflows least-privilege;
- third-party actions SHA-pinned;
- scheduled jobs do not silently rewrite trusted research.

## 46.10 Reusability

- works for non-software topics;
- repository metadata generic;
- Obsidian optional;
- Unicode titles safe;
- storage/sensitivity configurable;
- upgrades use migrations.

---

# 47. Immediate implementation batch

The next batch should stabilize what already exists before P5–P8 feature expansion.

1. Restore green GitHub Actions and inspect every failed job log.
2. Resolve Python UUIDv7/runtime support.
3. Fix segment/task-lease/gap/source writer-schema mismatches.
4. Validate every authoritative writer before persistence.
5. Fix evidence-edge test collection and add writer round-trip tests.
6. Implement the durable persistence model for authoritative `.research` records.
7. Add atomic writes and basic optimistic concurrency.
8. Require task idempotency and make leases collision-safe.
9. Align agent instructions, event schema, manifests, tool scopes, and runtime enforcement.
10. Make standalone evidence edges the single evidence-relationship authority.
11. Remove duplicated new-note/intake vocabularies and wire TemplateRegistry into note creation.
12. Fix remaining dashboard P0 correctness defects.
13. Update README/readiness claims only after CI is verified green.
14. Protect main / enforce required checks where supported.

Do not expand into autonomous browsing/parsing before this batch is stable.

---

# 48. References

Architecture/provenance:

- W3C PROV Primer: https://www.w3.org/TR/prov-primer/
- RFC 9562 UUIDs: https://www.rfc-editor.org/rfc/rfc9562.html
- Python 3.14 uuid documentation: https://docs.python.org/3.14/library/uuid.html
- Python 3.12 uuid documentation: https://docs.python.org/3.12/library/uuid.html
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
- Gitleaks Action organization-license documentation: https://github.com/gitleaks/gitleaks-action
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

---

# 50. Eight-round re-audit verification record

This section records the scope/result of the 2026-09-22 eight-pass audit. Normative changes are integrated into Sections 0, 3, and 45–47 rather than duplicated here.

| Pass | Scope | Result |
|---|---|---|
| 1 | Implementation completeness and previous-audit claims | Substantial progress confirmed, but previous completion/validation claims were too strong; current CI is red. |
| 2 | Schemas, state, IDs, authority boundaries | Found Python UUID support mismatch, authoritative-state persistence contradiction, duplicated vocabularies, incomplete snapshot/concurrency guarantees. |
| 3 | Agent instructions, manifests, tool contracts | Roles exist but enforcement is absent; several manifests cannot perform documented responsibilities; coordinator roles overlap. |
| 4 | Sources, segments, claims, evidence, intake, tests | Found writer/schema mismatches, missing referential validation, dual evidence authority, unstable intake identity, and uncollected evidence-edge tests. |
| 5 | Maintenance, CI, automation, packaging | Maintenance is an early evaluator; CI is red; dependency reproducibility and generated-drift enforcement are incomplete. |
| 6 | Dashboard UI/UX/data semantics | Previously identified P0 data-correctness and accessibility issues remain; state-driven redesign is pending. |
| 7 | Security, reliability, concurrency | Permissions are policy-only; atomic writes, optimistic concurrency, robust leases, quarantine/sandbox/SSRF/sensitivity controls remain incomplete. |
| 8 | Documentation, audit consistency, governance | Audit/README status drifted from reality; repository description is domain-specific; main is unprotected; source-authority guidance conflicts remain. |

## 50.1 Positive progress verified

The repository has moved materially forward: schemas/registries, package/tests, role manifests, CI/Dependabot/Gitleaks configuration, curator/OpenWolf files, evidence primitives, canonical local source registration, and state/health/maintenance builders now exist.

The current phase is best described as **integration hardening**, not missing foundation.

## 50.2 Evidence limitations

GitHub confirmed job-level failures for the latest CI run but the connector did not expose usable job logs in this audit session. Therefore job failure state is confirmed, source-level defects above are confirmed by code inspection, and exact attribution of each CI failure must be verified from Actions logs during implementation.

Do not weaken or disable gates merely to make CI green.

## 50.3 Next full-audit trigger

Run another full audit after the stabilization batch when:

- latest main CI is green;
- writer/schema round-trip tests exist;
- authoritative persistence policy is implemented;
- role/tool contracts are synchronized;
- dashboard P0 correctness defects are fixed.

Until then, Sections 3 and 47 are the immediate defect backlog.
