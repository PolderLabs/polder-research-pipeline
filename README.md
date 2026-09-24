---
type: guide
status: current
tags:
  - knowledge-base
  - research-pipeline
---

# Polder Research Pipeline

Polder is a repository-native system for source-backed research, evidence management, and knowledge maintenance. It combines typed Python records and schemas with human-readable Markdown notes and documented agent roles.

## Research modes

The pipeline supports two modes with different evidence claims:

- **Continuous intelligence** supports ongoing, bounded discovery, source processing, verification, and knowledge maintenance. It does not claim exhaustive search or systematic screening.
- **Systematic evidence review** requires a prespecified, frozen protocol; exact search logging and saved result exports; explicit candidate and duplicate records; independent human screening and extraction; adjudication; structured appraisal; and a generated, hash-indexed audit report before completion.

The systematic workflow is auditable within the local `.research/` store. Records and saved search exports are gitignored, reviewer IDs are not identity-authenticated, event coverage is incomplete, duplicate appraisal is not required by the completion gate, and the report is an index of hashes rather than a portable archive. PRISMA and Cochrane inform reporting and review controls; the implementation does not certify PRISMA compliance. See [Research methods](knowledge-base/00-home/research-methods.md) for the procedure, API, standards, and limits.

## Current implementation

- Typed schemas and Python APIs for runs, tasks, events, sources, segments, claims, entities, evidence, classifications, conflicts, gaps, handoffs, and maintenance.
- Automatic source, claim, entity, and segment tagging from a versioned taxonomy. Jev uses TypeSafe's API; Laya inference runs in-process locally. See [provider setup](knowledge-base/03-system/classification-providers.md).
- Protocol-first systematic-review records for protocols, searches, candidates, screening, extraction, appraisal, and review reports.
- Atomic schema-validated record writes and derived state/health builders.
- Obsidian-compatible vault, intake templates, note scaffolding, and vault integrity audit.
- A loopback-only browser control panel for configuration, provider credentials, Laya model setup, operational health, and research analytics.
- Documented role contracts under `agents/` and role capability manifests under `agents/roles/`. These are contracts; they do not imply that an autonomous multi-agent runtime or runtime permission enforcement is deployed.
- Tests, Ruff, schema checks, vault audit, and CI workflows. Current local validation is recorded in the audit status block, not inferred from this README.

## Start here

- [AGENTS.md](AGENTS.md): repository operating guide, local state bootstrap, validators, and intake.
- [Research methods](knowledge-base/00-home/research-methods.md): method selection and systematic-review lifecycle.
- [Evidence model](knowledge-base/00-home/evidence-model.md) and [provenance model](knowledge-base/00-home/provenance-model.md): record relationships and traceability.
- [Agent roles](agents/): responsibilities and capability manifests.
- [Audit and roadmap](knowledge-base/AUDIT.md): integration findings, known limitations, and planned work. Historical findings are labeled with their inspection date.
- [Knowledge base dashboard](knowledge-base/index.md): human-facing Obsidian entry point.

## Install a research workspace

From a POSIX shell with Git and Python 3.14+, bootstrap the complete project (knowledge base, schemas, agents, pipeline, and dashboard) into a new directory:

```sh
curl -fsSL https://raw.githubusercontent.com/PolderLabs/polder-research-pipeline/main/install.sh | sh -s -- --target ./my-research
cd ./my-research
.venv/bin/polder-research serve
```

Use `--with-dev` for pytest and Ruff or `--with-laya` to install Laya and its larger machine-learning dependencies. Laya model weights are downloaded separately from the dashboard. The installer refuses non-empty targets and creates a project-local virtual environment. See [install.sh](install.sh) for all options.

## Local control panel

Install the project, then run `polder-research serve` from the repository root and open the printed `http://127.0.0.1:8765` address. Use `--port` to select another local port. The interface edits the complete research configuration, stores an optional TypeSafe key in `.research/web-secrets.json` with owner-only permissions, and can download/load the selected Laya checkpoint into the server process. The service binds only to loopback. See [the control panel guide](knowledge-base/03-system/control-panel.md) for provider, privacy, and model setup details.

## Manual intake

For an individual artifact, place the original in `knowledge-base/90-inbox/raw/`, register it in the manifest, process it from the intake template, and link distilled notes to the source catalog. This workflow does not establish systematic search coverage or independent screening. Follow [the intake guide](knowledge-base/00-home/research-intake-guide.md); for a prespecified review, start with [Research methods](knowledge-base/00-home/research-methods.md) before searching.

## Repository map

| Path | Purpose |
|---|---|
| `src/polder_research/` | Typed record and workflow APIs, including `research_methods`. |
| `schemas/` | Canonical JSON Schemas for authoritative records. |
| `agents/` | Role instructions and machine-readable capability manifests. |
| `tests/` | Behavioral and schema tests. |
| `knowledge-base/` | Obsidian vault, guides, templates, research notes, and audit. |
| `.research/` | Local runtime records and exports; gitignored by the current persistence policy. |

## Validation

Run from the repository root:

```bash
pytest -q
ruff check src/polder_research
python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py
git diff --check
```

Schema and generated-state validation are also configured in CI. Do not claim current CI status from a local run; consult the latest workflow result.

## Current boundaries

- Authoritative `.research` records and search exports are local-only. A fresh clone does not contain a completed review record set.
- Reviewer IDs are self-asserted labels, not authenticated identities or proof of reviewer independence.
- Search exports must be available under the repository root and are verified by SHA-256 at search recording and run completion.
- A generated review report is a deterministic audit index of record IDs and hashes, not a bundled copy of all evidence.
- Agent role manifests describe capability boundaries, but the current implementation does not enforce them as a runtime authorization layer.
- Systematic-review completion requires a protocol-defined appraisal when marked required, but does not require duplicate independent appraisal or validate custom instrument logic.
- Automated source discovery, general-purpose autonomous workers, a shared durable backend, and portable review exports remain future work.

## Research standards

The method guide links to primary standards and handbooks, including PRISMA 2020, PRISMA-S, Cochrane Handbook guidance, W3C PROV-DM, and FAIR principles. These references inform workflow design; select and justify a framework suited to the question and evidence base rather than treating one framework as universal.

## License

Private repository. All rights reserved.
