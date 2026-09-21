---
type: guide
status: current
tags:
  - research-intake
  - guide
---

# Research Intake Guide

How to transform a raw artifact (PDF, URL, transcript, benchmark log) into a durable, linked note.

## The 6-step lifecycle

### 1. Drop

Copy the raw material to `90-inbox/raw/`. Preserve the original filename exactly.

Do not open, annotate, or rename the raw file at this stage. It is immutable.

### 2. Register

Add a row to `90-inbox/manifest.md` using the register script:

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py \
  --file my-report.pdf \
  --kind pdf \
  --owner curator
```

The manifest tracks the item through its entire lifecycle.

### 3. Triage

Assess the material:

- **Type**: paper, blog, video, benchmark, URL, transcript, or other.
- **Domain**: which numbered folder does it belong to?
- **Canonical URL**: where was it sourced from?
- **Access date**: when did you read it?
- **Decision impact**: does it affect any open decision in `04-decisions/`?
- **New vs. update**: does it supersede or extend an existing note?

Update the manifest row to `triaged`.

### 4. Process

Copy `99-templates/intake-record-template.md` to `90-inbox/processing/<descriptive-name>.md`.

Extract:
- Title, author/maintainer, publication date, version.
- One-paragraph summary.
- Key claims with evidence labels.
- Unanswered questions and gaps.
- Configurations, constraints, licenses.

Update manifest to `processing`.

### 5. Distill

Create or update a durable note in the appropriate domain folder:

- Copy `99-templates/research-note-template.md` for a new note.
- Update the frontmatter: `type`, `status: current`, `tags`.
- Label every claim: **Observed** / **Source-reported** / **Inference**.
- Cross-link to related notes.
- Update `06-sources/reference-catalog.md` with the source entry.

If conflicting claims exist, create a note from `99-templates/conflict-note-template.md` and link both sources.

Update manifest to `distilled`.

### 6. Close

1. Record the destination note path in the manifest `Outcome` column.
2. Move the processing note to `90-inbox/archive/filed/`.
3. Update manifest to `filed`.
4. The raw original stays in `90-inbox/raw/`.

If the material is intentionally not incorporated, close as `rejected` and archive in `90-inbox/archive/rejected/`.

## Evidence classification

| Label | Meaning |
|---|---|
| **Observed** | A direct measurement or finding from your own experiments |
| **Source-reported** | Claimed by the source; not independently verified |
| **Inference** | Your conclusion from multiple sources or reasoning |

## Provenance requirements

For every source:
- Exact URL or DOI.
- Access date.
- Author, publication, version.

## Conflict handling

When two sources make contradictory claims:
1. Create a conflict note from `99-templates/conflict-note-template.md`.
2. Link both sources.
3. Do not pick a favorite; present both with evidence classification.
4. Update the manifest `Outcome` to reference the conflict note.

## When to create a new note vs. update an existing one

- **New note**: the material introduces a genuinely new concept not covered by any existing note.
- **Update existing**: the material refines, corrects, or extends a concept already documented.

## Related

- [[00-home/knowledge-base-guide|Knowledge base guide]]
- [[00-home/vault-standards|Vault standards]]
- [[AGENTS|AGENTS.md]] — agent protocol
- `skills/obsidian-knowledgebase-curator/SKILL.md` — curator skill
