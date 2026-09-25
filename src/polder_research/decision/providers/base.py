"""Provider interface shared by decision workflows."""

from __future__ import annotations

from typing import Any, Protocol


class DecisionProvider(Protocol):
    def predict(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]: ...
