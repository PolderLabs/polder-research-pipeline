---
type: guide
status: current
topic: agent-protocols
tags:
  - knowledge-base
---

# Claude

This project uses OpenWolf for context management. For the full operating protocol — repository layout, intake lifecycle, validators, frontmatter schema, and wikilink rules — see [[AGENTS|AGENTS.md]].

The always-on rules live in `.claude/rules/openwolf.md`; hooks handle bookkeeping automatically. Load the `openwolf` skill or read `.wolf/OPENWOLF.md`; regenerate the session handoff with `/handoff`.
