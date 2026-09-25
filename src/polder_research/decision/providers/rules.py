"""Deterministic taxonomy baseline provider."""

from __future__ import annotations

from typing import Any

from ..state_builders import state_text


def predict(state: Any, taxonomy: dict[str, Any]) -> dict[str, Any]:
    normalized = state_text(state).casefold()
    categories: dict[str, float] = {}
    for key, entry in taxonomy.get("categories", {}).items():
        terms = [str(term).casefold() for term in entry.get("keywords", [])]
        categories[key] = float(any(term in normalized for term in terms))
    chosen = max(categories, key=categories.get) if categories else ""
    if chosen and not categories[chosen]:
        chosen = "other" if "other" in categories else None
    categories = {key: float(key == chosen) for key in categories}
    answers: dict[str, Any] = {}
    if categories:
        answers["category"] = {
            "type": "choice",
            "choice": chosen,
            "confidence": 1.0 if chosen else 0.0,
            "probabilities": categories,
        }
    for key, entry in taxonomy.get("tags", {}).items():
        terms = [str(term).casefold() for term in entry.get("keywords", [])]
        score = 1.0 if any(term in normalized for term in terms) else 0.0
        answers[f"tag_{key}"] = {"type": "noul", "noul": score}
    for key, entry in taxonomy.get("dimensions", {}).items():
        values = entry.get("values", {}) if isinstance(entry, dict) else {}
        scores = {
            label: float(
                any(
                    str(term).casefold() in normalized
                    for term in (value.get("keywords", []) if isinstance(value, dict) else [])
                )
            )
            for label, value in values.items()
        }
        choice = max(scores, key=scores.get) if scores else ""
        if choice and not scores[choice]:
            choice = "other" if "other" in scores else None
        scores = {label: float(label == choice) for label in scores}
        answers[f"dimension_{key}"] = {
            "type": "choice",
            "choice": choice,
            "probabilities": scores,
            "confidence": scores.get(choice, 0.0),
        }
    return {"model": "rules-v1", "answers": answers}
