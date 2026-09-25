"""In-process Laya Router adapter with automatic routing by default."""

from __future__ import annotations

import threading
from typing import Any

_LOCK = threading.RLock()
_ROUTERS: dict[tuple[str, int], Any] = {}


def router_for(device: str = "auto", max_loaded: int = 2) -> Any:
    key = (device, max_loaded)
    with _LOCK:
        if key not in _ROUTERS:
            from laya import Router

            options: dict[str, Any] = {"max_loaded": max_loaded}
            if device != "auto":
                options["device"] = device
            _ROUTERS[key] = Router(**options)
        return _ROUTERS[key]


def predict(state: Any, questions: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    mode = config.get("route_mode", "auto")
    model = config.get("explicit_model") or config.get("model", "english")
    options: dict[str, Any] = {}
    mapped_budgets = {
        key: value
        for key in ("max_len", "head_max_len")
        if isinstance((value := config.get(key)), dict)
    }
    for key in ("max_len", "head_max_len"):
        value = config.get(key)
        if value is not None and not isinstance(value, dict):
            options[key] = value
    if mapped_budgets:

        def set_routed_budgets(context: Any) -> None:
            decision = context.decision
            routed_model = decision.get("model") if isinstance(decision, dict) else None
            for key, values in mapped_budgets.items():
                if isinstance(routed_model, str) and isinstance(values.get(routed_model), int):
                    setattr(context, key, values[routed_model])

        options["on_predict_start"] = set_routed_budgets
    router = router_for(config.get("device", "auto"), int(config.get("max_loaded", 2)))
    if mode == "auto":
        result = router.predict(state, questions, **options)
    elif mode == "explicit":
        result = router.predict(state, questions, model=model, **options)
    else:
        raise ValueError("Laya route_mode must be auto or explicit")
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise RuntimeError("Laya returned an invalid System One response")
    resolved_model = result.get("model") or result.get("routing", {}).get("model")
    if not isinstance(resolved_model, str):
        raise RuntimeError("Laya omitted routed model identity")
    return result


def preload(model: str, device: str = "auto", max_loaded: int = 2) -> None:
    router_for(device, max_loaded).preload([model])
