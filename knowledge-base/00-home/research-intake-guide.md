---
type: guide
status: current
tags:
  - research-intake
  - guide
---

# Research Intake Guide

How to transform a raw artifact (PDF, URL, transcript, benchmark log) into a durable, linked note.

For a prespecified systematic review, follow [[research-methods|Research Methods and Auditability]] before searching. This intake guide describes individual artifact processing; it does not establish comprehensive search coverage or independent screening by itself.

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

For a seed list, use `--manifest` with a CSV or JSON Lines file. Each row
requires `title` and exactly one of `canonical_url` or `local_file`. A URL-only
row is recorded with `acquisition_status: unacquired`; it has no content hash until you acquire the
material. A local file must already be inside `90-inbox/raw/` and is hashed
when registered. Optional columns are `source_type`, `media_type`,
`retrieved_at`, `tags`, `source_class`, and `notes`. Tags can be separated by
commas or semicolons in CSV. Types are checked against the source schema, and
invalid rows stop the batch before records are written.

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py \
  --root /path/to/workspace --manifest seed-list.csv --dry-run
python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py \
  --root /path/to/workspace --manifest seed-list.csv
```

The command reports each planned registration. Re-running the same manifest
reuses canonical sources and does not add duplicate queue rows. `source_class`
is an optional project-specific triage label; it is not a trust or appraisal
rating.

Acquire a previously registered URL reference after placing its downloaded artifact in
`90-inbox/raw/`:

```bash
polder-research --root /path/to/workspace source-acquire \
  --source-id src_<uuid> --file downloaded-page.html
```

Acquisition records its content hash and retrieval time, performs source
classification, and refuses promotion when that content hash already belongs
to another source record.

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
