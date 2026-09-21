# Memory

## Project conventions

- Vault root IS the repo root. Every `.md` file is a note.
- Wikilinks: vault-root-relative, no `.md` extension.
- Frontmatter: `type`, `status`, `tags` required on every note.
- Orphan = `(p.file.inlinks?.length ?? 0) === 0`.
- Dataview JS: `dv.fileLink()` → `dv.span(link, {container})`. `p.tags.array` is a getter.

## Research intake lifecycle

1. Drop raw file to `90-inbox/raw/`
2. Register: `intake_register.py --file <name> --kind <kind> --owner <owner>`
3. Create processing note from `99-templates/intake-record-template.md`
4. Distill: extract claims, label Observed / Source-reported / Inference, cross-link
5. Close: update manifest status, move processing note to `archive/filed/`
