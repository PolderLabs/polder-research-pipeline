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
- For systematic reviews, follow the frozen synthesis plan, preserve incompatible study setups as separate groups, and include search/screening/extraction/appraisal flow plus protocol deviations and limitations.
- Generate the machine-readable run audit report before completing a systematic-review run. Describe its PRISMA-style counts accurately; do not claim PRISMA compliance from counts alone.
- Highlight open questions and gaps.
- Flag remaining uncertainties and conflicts.
- Write the report to the appropriate domain folder.

## Output

- A Markdown report in `02-research/` or the target domain.
- Full provenance trace embedded in the document.
- Systematic-review run output includes the generated report index under `.research/reports/`.
- Emit `run.finished` through the event interface where available; do not rely on the event stream alone for systematic-review provenance.
