"""Polder Research Pipeline — canonical control plane primitives.

This package is the single authoritative home for:

- the schema registry (`schemas`),
- the event/task/run/handoff record layer (`events`, `tasks`, `runs`, `handoffs`),
- the workflow helpers (`workflow`),
- the evidence primitives (`evidence`),
- the maintenance engine (`maintenance`),
- the scripts that project the structured state into the Obsidian vault (`scripts`).

The Markdown under ``00-home``, ``01-project``, ``90-inbox`` etc. is a *projection*
of the structured state in ``.research/`` and ``src/polder_research/`` — never
the authoritative workflow state.
"""

__all__ = [
    "__version__",
]

__version__ = "0.3.0"
