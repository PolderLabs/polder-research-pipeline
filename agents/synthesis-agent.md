---
type: guide
status: current
tags:
  - agents
  - synthesis
---

# Synthesis Agent

Produces final research output from verified claims and evidence.

## Responsibilities

- Synthesize verified claims into a coherent narrative.
- Produce a report that traces every claim to its evidence edge and source.
- Highlight open questions and gaps.
- Flag remaining uncertainties and conflicts.
- Write the report to the appropriate domain folder.

## Output

- A Markdown report in `02-research/` or the target domain.
- Full provenance trace embedded in the document.
- Events: `run.finished` on completion.
