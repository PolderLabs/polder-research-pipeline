---
type: guide
status: current
tags:
  - research-intake
---

# Research Inbox

Drop raw research material here without pre-formatting it.

## Locations

- `raw/` — immutable originals; preserve original filename. See [[90-inbox/raw/README|drop-zone contract]].
- `processing/` — one agent-owned processing note per item.
- `archive/filed/` — completed intake records.
- `archive/rejected/` — material intentionally not incorporated.
- `manifest.md` — queue and lifecycle tracker.

## Agent contract

1. Register in `manifest.md` BEFORE processing.
2. Never delete, overwrite, or move the raw original.
3. Only the processing record moves to archive when the lifecycle closes.
4. Heavy binaries are not committed — see `90-inbox/raw/.gitignore`.

See [[00-home/research-intake-guide|the research intake guide]] for the full lifecycle.
