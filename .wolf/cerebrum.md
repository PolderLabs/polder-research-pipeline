# OpenWolf Cerebrum

The cognitive/decision spine — invoked at session start to load canonical state, gatework, and intent.

## At session start

1. Read `.wolf/OPENWOLF.md` — vault structure, key guides, validators.
2. Read `.wolf/anatomy.md` — file-by-file decision context.
3. Run `vault_audit.py` to verify integrity before doing any work.
4. Inspect `90-inbox/` for newly dropped items.
5. Inspect `.research/state.json` for current run state.

## Vault integrity gates

- No `ORPHANS:` output from `vault_audit.py`.
- No `UNREACHABLE:` output.
- No frontmatter issues.
- Exit code 0.

## Decision rules

- Single source of truth: never duplicate vocabulary, paths, or enum values across files.
- Evidence over assertion: every claim in the knowledge base must trace to a source.
- Idempotent operations: any operation may be retried safely.

## Process

1. Drop, register, process, distill, close — for raw material in `90-inbox/`.
2. Agents emit events to `.research/events/` for every action.
3. Schema registry is canonical for all record types.
4. Tests are evidence, not decoration — every test must defend a contract.

## Failures

- If `vault_audit.py` reports orphans or broken links: fix the document, not the audit.
- If `.research/state.json` shows `failed` runs or tasks: investigate the event log.
- If a test fails: fix the implementation; tests are the contract.
