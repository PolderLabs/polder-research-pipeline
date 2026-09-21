# OpenWolf

This project uses OpenWolf for context management. Read and follow `.wolf/OPENWOLF.md` at session start.

## Vault structure

|Folder|Purpose|
|---|---|
|`00-home`|Navigation hub, operating guides, knowledge-base standards.|
|`01-project`|Goals, requirements, ethics, stable project constraints.|
|`02-research`|Distilled research: models, papers, tools, technology landscape.|
|`03-system`|Architecture, performance, transports, deployment, runtime design.|
|`04-decisions`|Decision records, comparison matrices, risk assessments.|
|`05-operations`|Roadmaps, experiments, benchmarks, runbooks.|
|`06-sources`|Source catalog and evidence records.|
|`90-inbox`|Raw unprocessed material and the intake queue.|
|`99-templates`|Copyable canonical note templates.|

## Key guides

- `00-home/knowledge-base-guide.md` — folder contract, frontmatter schema, link conventions, tag taxonomy.
- `00-home/research-intake-guide.md` — detailed intake lifecycle and evidence classification rules.
- `00-home/vault-standards.md` — naming, wikilink format, frontmatter values, orphan policy.
- `90-inbox/README.md` — inbox operating rules, raw immutability policy, lifecycle states.
- `99-templates/intake-record-template.md` — template for the processing record.

## Validators

All scripts live in `skills/obsidian-knowledgebase-curator/scripts/`. Run from the repo root.

```bash
python3 skills/obsidian-knowledgebase-curator/scripts/vault_audit.py
```
