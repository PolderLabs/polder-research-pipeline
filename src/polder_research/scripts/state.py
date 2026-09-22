"""state build and health build commands."""

from __future__ import annotations

from ..maintenance import build_health, save_health
from ..workflow import build_state, save_state


def cmd_build_state() -> int:
    state = build_state()
    save_state(state)
    print(
        f"state.json written — {state['events']['total']} events, "
        f"{state['tasks']['total']} tasks, {state['runs']['total']} runs"
    )
    return 0


def cmd_build_health() -> int:
    health = build_health()
    save_health(health)
    issues = len(health["issues"])
    print(f"health.json written — overall: {health['overall']}, issues: {issues}")
    return 0
