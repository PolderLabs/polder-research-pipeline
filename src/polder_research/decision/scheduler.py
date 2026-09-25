"""Order-preserving batch execution for a local Laya Router."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class LayaBatchScheduler:
    """Collect compatible local requests and use Router.predict_batch."""

    def __init__(
        self,
        router: Any,
        *,
        batch_size: int = 32,
        predict_options: dict[str, Any] | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.router = router
        self.batch_size = batch_size
        self.predict_options = dict(predict_options or {})
        self._items: list[dict[str, Any]] = []

    def submit(self, request: dict[str, Any]) -> int:
        if not isinstance(request.get("state"), str | dict | list):
            raise ValueError("request state must be text, object, or array")
        if not isinstance(request.get("questions"), dict) or not request["questions"]:
            raise ValueError("request questions must be a non-empty object")
        self._items.append(dict(request))
        return len(self._items) - 1

    def flush(self, *, max_items: int | None = None) -> list[dict[str, Any]]:
        """Predict queued requests, preserving their submission order."""
        if not self._items:
            return []
        cap = self.batch_size if max_items is None else min(max_items, self.batch_size)
        if cap < 1:
            raise ValueError("max_items must be positive")
        selected, self._items = self._items[:cap], self._items[cap:]
        groups: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        for index, request in enumerate(selected):
            policy_key = str(request.get("compatibility_key", "default"))
            groups[policy_key].append((index, request))
        output: list[dict[str, Any] | None] = [None] * len(selected)
        for items in groups.values():
            requests = []
            for _, request in items:
                submitted = {
                    key: value
                    for key, value in request.items()
                    if key in {"state", "questions", "task", "lang", "lang_guess"}
                }
                # Laya's automatic router is selected by omitting ``model``.
                # Passing the local policy marker ``auto`` through would ask
                # the Router to load a checkpoint with that literal name.
                model = request.get("model")
                if isinstance(model, str) and model and model != "auto":
                    submitted["model"] = model
                requests.append(submitted)
            results = self.router.predict_batch(
                requests, batch_size=self.batch_size, **self.predict_options
            )
            if len(results) != len(items):
                raise RuntimeError("Laya Router returned a mismatched batch size")
            for (index, _), result in zip(items, results, strict=True):
                output[index] = result
        return [result for result in output if result is not None]
