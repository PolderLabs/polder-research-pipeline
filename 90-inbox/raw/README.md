---
type: inbox
status: current
tags:
  - intake
---

# Drop Zone

Drop raw research material here. Anything goes — do not pre-format, rename, or annotate.

## Supported types

- PDFs (papers, reports)
- Web pages (saved as HTML, MHTML, or PDF)
- Academic papers (arXiv, conference proceedings)
- Transcripts (YouTube, podcasts, talks)
- Screenshots
- Benchmark logs
- URL lists

## Immutability

The raw original is never edited, overwritten, or deleted. Once dropped, it stays in `raw/` for the lifetime of the vault.

## Quick drop

```bash
cp "$REPO/my-paper.pdf" ./my-paper.pdf   # adjust to your repository path
python3 skills/obsidian-knowledgebase-curator/scripts/intake_register.py \
  --file my-paper.pdf --kind pdf --owner curator
```

## Binaries

Heavy binary files are excluded from version control. See `.gitignore` in this folder. Keep small text files (`.md`, `.txt`, `.json`, `.yaml`, `.yml`) for transparency.

## Next step

After dropping, register the item in `90-inbox/manifest.md`, then start a processing note from `99-templates/intake-record-template.md`. See the full contract in `skills/obsidian-knowledgebase-curator/SKILL.md`.
