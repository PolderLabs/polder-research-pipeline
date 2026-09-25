"""Versioned provider-neutral question packs for bounded workflow decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QuestionPack:
    id: str
    purpose: str
    questions: dict[str, dict[str, Any]]
    consequence_class: str
    supported_providers: tuple[str, ...] = ("jev", "laya")
    remote_processing_allowed: bool = False

    @property
    def sha256(self) -> str:
        encoded = json.dumps(
            {
                "id": self.id,
                "purpose": self.purpose,
                "questions": self.questions,
                "consequence_class": self.consequence_class,
                "supported_providers": self.supported_providers,
                "remote_processing_allowed": self.remote_processing_allowed,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def validate_provider(self, provider: str, *, max_options: int | None = None) -> None:
        if provider not in self.supported_providers:
            raise ValueError(f"provider {provider!r} is not supported by question pack {self.id!r}")
        if max_options is not None:
            for name, question in self.questions.items():
                criteria = question.get("criteria")
                if (
                    question.get("type") == "choice"
                    and isinstance(criteria, dict)
                    and len(criteria) > max_options
                ):
                    raise ValueError(f"question {name!r} exceeds the provider option budget")


def _choice(instructions: str, labels: list[str]) -> dict[str, Any]:
    return {"type": "choice", "instructions": instructions, "criteria": dict.fromkeys(labels)}


INTAKE_TRIAGE = QuestionPack(
    id="intake/triage@1",
    purpose="intake-triage",
    consequence_class="queue-only",
    questions={
        "detected_language": _choice(
            "What language is the material primarily in?", ["en", "nl", "other", "unclear"]
        ),
        "likely_source_family": _choice(
            "Which source family best fits the material?",
            ["paper", "documentation", "repository", "dataset", "media", "other"],
        ),
        "requires_ocr": {
            "type": "noul",
            "instructions": "Does this item likely require OCR before useful text can be extracted?",
        },
        "translation_required": {
            "type": "noul",
            "instructions": "Will translation likely be required for the research team to use this item?",
        },
        "possible_sensitive_content": {
            "type": "noul",
            "instructions": "Does the material appear to contain potentially sensitive or personal information?",
        },
        "extraction_complexity": {
            "type": "score",
            "instructions": "How complex is reliable extraction?",
            "criteria": ["low", "moderate", "high"],
        },
    },
)

EXTRACTION_QUALITY = QuestionPack(
    id="extraction/quality@1",
    purpose="extraction-quality",
    consequence_class="reversible-reprocessing",
    questions={
        "ocr_corruption": {
            "type": "noul",
            "instructions": "Is the extracted text materially corrupted?",
        },
        "missing_context": {
            "type": "noul",
            "instructions": "Is important context missing from the extracted segment?",
        },
        "layout_or_table_loss": {
            "type": "noul",
            "instructions": "Was meaningful layout, table, or code structure likely lost?",
        },
        "locator_quality": {
            "type": "score",
            "instructions": "How useful is the source locator?",
            "criteria": ["poor", "usable", "precise"],
        },
        "language_mismatch": {
            "type": "noul",
            "instructions": "Does the extracted text language appear inconsistent with the source metadata?",
        },
    },
)

SOURCE_PRIORITY = QuestionPack(
    id="source/priority@1",
    purpose="continuous-intelligence-priority",
    consequence_class="queue-order-only",
    remote_processing_allowed=True,
    questions={
        key: {"type": "score", "instructions": prompt, "criteria": ["low", "moderate", "high"]}
        for key, prompt in {
            "topical_relevance": "How relevant is this source to the active research scope?",
            "primary_evidence_likelihood": "How likely is this source to contain primary evidence?",
            "novelty": "How likely is this source to add novel information?",
            "technical_depth": "How much implementation or methodological detail does it appear to contain?",
            "benchmark_relevance": "How relevant does it appear to be to benchmarks or datasets?",
            "time_sensitivity": "How time-sensitive is review of this source?",
        }.items()
    },
)

REVIEW_PRIORITY = QuestionPack(
    id="review/priority@1",
    purpose="review-queue-priority",
    consequence_class="queue-order-only",
    questions={
        "urgency": {
            "type": "score",
            "instructions": "How urgently should a human review this item?",
            "criteria": ["routine", "soon", "urgent"],
        },
        "downstream_impact": {
            "type": "score",
            "instructions": "How many important downstream decisions could be affected?",
            "criteria": ["limited", "moderate", "broad"],
        },
        "anomaly": {
            "type": "noul",
            "instructions": "Does this item contain an unusual disagreement or drift signal?",
        },
    },
)


def task_routing_pack(available_roles: list[str]) -> QuestionPack:
    roles = list(dict.fromkeys(available_roles))
    if not roles:
        raise ValueError("task routing requires at least one deterministically permitted role")
    return QuestionPack(
        id="task/routing@1",
        purpose="task-routing",
        consequence_class="suggestion-only",
        questions={
            "role": _choice("Which permitted role is the best fit for this task?", roles),
            "needs_human": {
                "type": "noul",
                "instructions": "Should the task be escalated to a human or orchestrator?",
            },
        },
    )
