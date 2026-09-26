"""Replay and evaluate immutable classification records.

This module deliberately does not modify evidence records.  Replaying invokes
``classify_text`` for existing evidence and relies on its record key for
idempotency.  Evaluation reads separately supplied, human-authored gold labels
and never promotes a model prediction to a gold label.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import re
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema

from .atomic import write_atomic
from .classification import (
    _question_hash,
    _questions,
    _requested_model,
    classify_text,
    select_provider,
)
from .decision.scheduler import LayaBatchScheduler
from .decision.state_builders import build_state_for_target, clip_state, state_text
from .locking import LockBusyError, acquire_file_lock, release_file_lock
from .schemas import SchemaError, registry_for_root

_KINDS = ("source", "segment", "claim", "entity")
_DIRECTORIES = {
    "source": "sources",
    "segment": "segments",
    "claim": "claims",
    "entity": "entities",
}
_SENSITIVITY_ORDER = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
_JOB_DIRECTORY = "classification-jobs"


def _sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _hash(text: Any) -> str:
    encoded = (
        json.dumps(text, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if isinstance(text, dict | list)
        else str(text)
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _classification_config(root: Path) -> dict[str, Any]:
    from .decision.config import effective_classification, load_config

    return effective_classification(load_config(root))


def _policy_for(
    kind: str, record: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    related = [record]
    if kind == "segment":
        related.append(sources.get(str(record.get("source_id", "")), {}))
    elif kind in {"claim", "entity"}:
        related.extend(
            sources.get(str(source_id), {}) for source_id in record.get("source_ids", [])
        )
    sensitivity = max(
        (str(item.get("sensitivity", "public")) for item in related),
        key=lambda value: _SENSITIVITY_ORDER.get(value, 3),
        default="public",
    )
    approval_sources = (
        [record]
        if kind == "source"
        else [item for item in related if item.get("id", "").startswith("src_")]
    )
    return {
        "sensitivity": sensitivity,
        "personal_data": kind == "entity"
        and record.get("entity_kind") == "person"
        or any(bool(item.get("personal_data", False)) for item in related),
        "remote_processing_allowed": bool(approval_sources)
        and all(item.get("remote_processing_allowed", False) is True for item in approval_sources),
    }


def _is_sensitive_policy(policy: dict[str, Any]) -> bool:
    return bool(policy.get("personal_data")) or policy.get("sensitivity") != "public"


def _laya_batch_scheduler(config: dict[str, Any]) -> LayaBatchScheduler:
    """Build one local scheduler using the same routing settings as single calls."""
    from .decision.providers.laya_inprocess import router_for

    settings = config.get("laya", {})
    if not isinstance(settings, dict) or settings.get("transport", "inprocess") != "inprocess":
        raise ValueError("Laya batch replay requires the in-process transport")
    mapped_budgets = {
        key: value
        for key in ("max_len", "head_max_len")
        if isinstance((value := settings.get(key)), dict)
    }
    options: dict[str, Any] = {
        key: settings[key]
        for key in ("max_len", "head_max_len")
        if settings.get(key) is not None and not isinstance(settings.get(key), dict)
    }
    if mapped_budgets:

        def set_routed_budgets(context: Any) -> None:
            decision = context.decision
            routed_model = decision.get("model") if isinstance(decision, dict) else None
            for key, values in mapped_budgets.items():
                if isinstance(routed_model, str) and isinstance(values.get(routed_model), int):
                    setattr(context, key, values[routed_model])

        options["on_predict_start"] = set_routed_budgets
    return LayaBatchScheduler(
        router_for(settings.get("device", "auto"), int(settings.get("max_loaded", 2))),
        batch_size=32,
        predict_options=options,
    )


def _root(repository_root: str | Path | None) -> Path:
    return Path(repository_root or ".").resolve()


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _input_for(kind: str, record: dict[str, Any]) -> dict[str, Any]:
    """Use the same versioned builder as first-pass registration."""
    return build_state_for_target(kind, record).state


def evidence_targets(
    repository_root: str | Path | None = None, *, kinds: Iterable[str] = _KINDS
) -> list[dict[str, Any]]:
    """Load usable existing evidence without mutating it.

    Invalid JSON and records without a non-empty identifier are skipped; their
    paths are returned by :func:`replay_existing` as skipped items.
    """
    root = _root(repository_root)
    registry = registry_for_root(root, allow_package_fallback=True)
    selected = tuple(dict.fromkeys(kinds))
    invalid = set(selected).difference(_KINDS)
    if invalid:
        raise ValueError(f"unsupported target kinds: {', '.join(sorted(invalid))}")
    sources = {
        str(record.get("id")): record
        for path in (root / ".research" / "sources").glob("*.json")
        if (record := _load_json(path))
        and isinstance(record.get("id"), str)
        and path.name == f"{record['id']}.json"
        and registry.is_valid("source", record)
    }
    targets: list[dict[str, Any]] = []
    for kind in selected:
        for path in sorted((root / ".research" / _DIRECTORIES[kind]).glob("*.json")):
            record = _load_json(path)
            if not record or not isinstance(record.get("id"), str) or not record["id"]:
                continue
            if path.name != f"{record['id']}.json" or not registry.is_valid(kind, record):
                continue
            state = _input_for(kind, record)
            if state_text(state).strip():
                targets.append(
                    {
                        "kind": kind,
                        "id": record["id"],
                        "text": state,
                        "path": path,
                        "policy_metadata": _policy_for(kind, record, sources),
                    }
                )
    return targets


def _taxonomy_identity(config: dict[str, Any]) -> tuple[str, str]:
    taxonomy = config.get("taxonomy", {})
    if not isinstance(taxonomy, dict):
        raise ValueError("classification taxonomy must be a mapping")
    return _hash(json.dumps(taxonomy, sort_keys=True, separators=(",", ":"))), str(
        taxonomy.get("version", "1")
    )


def _replay_manifest(config: dict[str, Any], root: Path) -> dict[str, Any]:
    encoded = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    providers = {"rules": None, "jev": "typesafe-sdk", "laya": "laya"}
    try:
        polder_version = importlib.metadata.version("polder-research-pipeline")
    except importlib.metadata.PackageNotFoundError:
        polder_version = "0.2.0"
    runtime: dict[str, str | None] = {"polder_version": polder_version}
    for _provider, package in providers.items():
        if package:
            try:
                runtime[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                runtime[package] = None
    code_files = [
        root / "src" / "polder_research" / "classification" / "__init__.py",
        root / "src" / "polder_research" / "classification_ops.py",
        *sorted((root / "src" / "polder_research" / "decision").rglob("*.py")),
        root / "schemas" / "classification.schema.json",
        root / "schemas" / "classification-replay-job.schema.json",
    ]
    code_identity = [
        (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in code_files
        if path.is_file()
    ]
    return {
        "execution_config_sha256": _hash(encoded),
        "code_sha256": _hash(json.dumps(code_identity, separators=(",", ":"))),
        "question_set_sha256": _question_hash(config.get("taxonomy", {})),
        "state_builder_ids": {
            "source": "source/metadata@1",
            "segment": "segment/default@1",
            "claim": "claim/default@1",
            "entity": "entity/default@1",
        },
        "provider_runtime": runtime,
        "remote_processing_policy": config.get("remote_processing", {}),
    }


def _job_dir(root: Path) -> Path:
    return root / ".research" / _JOB_DIRECTORY


def _job_path(root: Path, job_id: str, version: int) -> Path:
    return _job_dir(root) / f"{job_id}.v{version:04d}.json"


def _latest_job(root: Path, job_id: str) -> dict[str, Any]:
    if not isinstance(job_id, str) or not re.fullmatch(
        r"crj_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", job_id
    ):
        raise ValueError("classification replay job ID is invalid")
    versions = sorted(_job_dir(root).glob(f"{job_id}.v*.json"))
    if not versions:
        raise ValueError(f"classification replay job not found: {job_id}")
    job = _load_json(versions[-1])
    if not job:
        raise ValueError(f"classification replay job is unreadable: {job_id}")
    registry_for_root(root, allow_package_fallback=True).validate("classification-replay-job", job)
    return job


def _write_job(root: Path, job: dict[str, Any]) -> dict[str, Any]:
    next_job = dict(job)
    next_job["version"] = int(job.get("version", 0)) + 1
    next_job["updated_at"] = _now()
    write_atomic(
        _job_path(root, next_job["id"], next_job["version"]),
        next_job,
        schema_name="classification-replay-job",
        registry=registry_for_root(root, allow_package_fallback=True),
    )
    return next_job


def _job_lock(root: Path, job_id: str):
    path = root / ".research" / "locks" / f"{job_id}.lock"
    try:
        return acquire_file_lock(path)
    except LockBusyError as exc:
        raise RuntimeError(f"classification replay job is already running: {job_id}") from exc


def _release_job_lock(handle) -> None:
    release_file_lock(handle)


def _job_summary(job: dict[str, Any], *, mode: str) -> dict[str, Any]:
    targets = job["targets"]
    status = Counter(target["status"] for target in targets)
    return {
        "mode": mode,
        "job_id": job["id"],
        "job_status": job["status"],
        "job_version": job["version"],
        "provider_override": job["provider_override"],
        "taxonomy_sha256": job["taxonomy_sha256"],
        "taxonomy_version": job["taxonomy_version"],
        "selected": len(targets),
        "by_kind": dict(sorted(Counter(target["target_kind"] for target in targets).items())),
        "by_status": dict(sorted(status.items())),
        "results": [
            {
                "kind": target["target_kind"],
                "id": target["target_id"],
                "provider": target["provider"],
                "status": target["status"],
                "attempts": target["attempts"],
                "classification_id": target["classification_id"],
            }
            for target in targets
        ],
    }


def replay_existing(
    repository_root: str | Path | None = None,
    *,
    kinds: Iterable[str] = _KINDS,
    dry_run: bool = False,
    limit: int | None = None,
    provider: str | None = None,
    resume_job_id: str | None = None,
) -> dict[str, Any]:
    """Classify existing evidence records, preserving immutable predictions.

    ``classify_text`` returns an existing record for an identical input and
    configured taxonomy/provider/model/threshold, making repeated replays
    idempotent.  This operation intentionally does not merge proposals back
    into evidence; reviewers retain control over application of metadata.
    """
    if provider not in {None, "rules", "jev", "laya"}:
        raise ValueError("provider must be rules, jev, or laya")
    if resume_job_id and dry_run:
        raise ValueError("cannot dry-run a resumed job")
    if resume_job_id and (limit is not None or provider is not None or tuple(kinds) != _KINDS):
        raise ValueError(
            "resume uses the persisted target list; omit --kind, --limit, and --provider"
        )
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")
    root = _root(repository_root)
    config = _classification_config(root)
    taxonomy_sha256, taxonomy_version = _taxonomy_identity(config)
    replay_manifest = _replay_manifest(config, root)
    targets = evidence_targets(root, kinds=kinds) if not resume_job_id else []
    if limit is not None:
        targets = targets[:limit]
    if dry_run:
        preview = []
        for item in targets:
            selected_provider = provider or select_provider(
                config, item["kind"], item["policy_metadata"]
            )
            blocked = selected_provider == "jev" and _is_sensitive_policy(item["policy_metadata"])
            preview.append(
                {
                    "kind": item["kind"],
                    "id": item["id"],
                    "provider": selected_provider,
                    "sensitivity": item["policy_metadata"]["sensitivity"],
                    "status": "blocked" if blocked else "pending",
                }
            )
        return {
            "mode": "dry_run",
            "provider_override": provider,
            "taxonomy_sha256": taxonomy_sha256,
            "taxonomy_version": taxonomy_version,
            "selected": len(preview),
            "targets": preview,
        }

    if resume_job_id:
        job = _latest_job(root, resume_job_id)
        if job["taxonomy_sha256"] != taxonomy_sha256 or job["taxonomy_version"] != taxonomy_version:
            raise ValueError("current taxonomy differs from replay job; start a new job")
        for key, expected in replay_manifest.items():
            if job.get(key) != expected:
                raise ValueError(f"replay configuration differs at {key}; start a new job")
        job["status"] = "running"
    else:
        job_id = f"crj_{uuid.uuid7()}"
        job = {
            "id": job_id,
            "schema_version": 1,
            "version": 0,
            "status": "running",
            "provider_override": provider,
            "taxonomy_sha256": taxonomy_sha256,
            "taxonomy_version": taxonomy_version,
            **replay_manifest,
            "created_at": _now(),
            "updated_at": _now(),
            "targets": [],
        }
        maximum_chars = int(config.get("max_input_chars", 12000))
        for item in targets:
            selected_provider = provider or select_provider(
                config, item["kind"], item["policy_metadata"]
            )
            policy = item["policy_metadata"]
            blocked = selected_provider == "jev" and _is_sensitive_policy(policy)
            job["targets"].append(
                {
                    "target_kind": item["kind"],
                    "target_id": item["id"],
                    "input_sha256": _hash(clip_state(item["text"], maximum_chars)),
                    "provider": selected_provider,
                    "sensitivity": policy["sensitivity"],
                    "personal_data": policy["personal_data"],
                    "status": "blocked" if blocked else "pending",
                    "attempts": 0,
                    "classification_id": None,
                    "error": "sensitive targets cannot be sent to Jev" if blocked else None,
                }
            )
    lock = _job_lock(root, job["id"])
    try:
        job = _write_job(root, job)
        live_targets = {
            (item["kind"], item["id"]): item for item in evidence_targets(root, kinds=_KINDS)
        }
        laya_batch: list[tuple[dict[str, Any], dict[str, Any]]] = []

        def classify_one(
            target: dict[str, Any],
            item: dict[str, Any],
            *,
            provider_result: dict[str, Any] | None = None,
            start: bool = True,
        ) -> None:
            nonlocal job
            if start:
                target["status"] = "running"
                target["attempts"] += 1
                target["error"] = None
                job = _write_job(root, job)
            try:
                result = classify_text(
                    item["text"],
                    target_kind=target["target_kind"],
                    target_id=target["target_id"],
                    repository_root=root,
                    provider=target["provider"],
                    policy_metadata=item["policy_metadata"],
                    provider_result=provider_result,
                )
            except (OSError, ValueError, RuntimeError):
                target.update(
                    {
                        "status": "failed",
                        "classification_id": None,
                        "error": "classification invocation failed",
                    }
                )
            else:
                if result is None:
                    target.update({"status": "disabled", "classification_id": None})
                elif result.get("disposition") == "failed":
                    target.update(
                        {
                            "status": "failed",
                            "classification_id": result.get("id"),
                            "error": result.get("error"),
                        }
                    )
                else:
                    target.update({"status": "completed", "classification_id": result.get("id")})
            target["updated_at"] = _now()
            job = _write_job(root, job)

        for target in job["targets"]:
            # A process may exit after persisting "running" but before writing
            # its result.  Holding the job lock proves no other replay worker is
            # active, so recover that interrupted target just like a failure.
            if target["status"] not in {"pending", "failed", "running"}:
                continue
            item = live_targets.get((target["target_kind"], target["target_id"]))
            if (
                not item
                or _hash(clip_state(item["text"], int(config.get("max_input_chars", 12000))))
                != target["input_sha256"]
            ):
                target.update(
                    {
                        "status": "failed",
                        "error": "target is missing or its input changed",
                        "updated_at": _now(),
                    }
                )
                job = _write_job(root, job)
                continue
            if target["provider"] == "jev" and _is_sensitive_policy(item["policy_metadata"]):
                target.update(
                    {
                        "status": "blocked",
                        "error": "sensitive targets cannot be sent to Jev",
                        "updated_at": _now(),
                    }
                )
                job = _write_job(root, job)
                continue
            if (
                target["provider"] == "laya"
                and config.get("enabled", True)
                and isinstance(config.get("laya"), dict)
                and config["laya"].get("transport", "inprocess") == "inprocess"
                and any(
                    config.get("taxonomy", {}).get(key)
                    for key in ("categories", "tags", "dimensions")
                )
            ):
                # Persist the running state before dispatching the local batch.
                # A process crash therefore resumes these targets exactly like a
                # single-request replay attempt.
                target["status"] = "running"
                target["attempts"] += 1
                target["error"] = None
                job = _write_job(root, job)
                laya_batch.append((target, item))
                continue
            classify_one(target, item)

        if laya_batch:
            try:
                scheduler = _laya_batch_scheduler(config)
                questions = _questions(config.get("taxonomy", {}))
                requested_model = _requested_model(config, "laya")
                responses: list[dict[str, Any]] = []
                for _target, item in laya_batch:
                    scheduler.submit(
                        {
                            "state": clip_state(
                                item["text"], int(config.get("max_input_chars", 12000))
                            ),
                            "questions": questions,
                            "model": requested_model,
                            # Current taxonomy and provider settings are shared
                            # for a replay job; retain an explicit key so future
                            # heterogeneous jobs cannot be co-batched by accident.
                            "compatibility_key": _hash(
                                {
                                    "questions": questions,
                                    "requested_model": requested_model,
                                    "laya": config.get("laya", {}),
                                }
                            ),
                        }
                    )
                while len(responses) < len(laya_batch):
                    responses.extend(scheduler.flush())
                if len(responses) != len(laya_batch):
                    raise RuntimeError("Laya batch replay returned a mismatched result count")
            except (ImportError, OSError, ValueError, RuntimeError):
                for target, _item in laya_batch:
                    target.update(
                        {
                            "status": "failed",
                            "classification_id": None,
                            "error": "classification invocation failed",
                            "updated_at": _now(),
                        }
                    )
                    job = _write_job(root, job)
            else:
                for (target, item), response in zip(laya_batch, responses, strict=True):
                    classify_one(target, item, provider_result=response, start=False)
        statuses = {target["status"] for target in job["targets"]}
        job["status"] = (
            "completed"
            if not statuses.intersection({"pending", "running", "failed", "blocked"})
            else "completed_with_issues"
        )
        job = _write_job(root, job)
        from .decision.projection import rebuild_effective_projection

        rebuild_effective_projection(root)
        return _job_summary(job, mode="resume" if resume_job_id else "replay")
    finally:
        _release_job_lock(lock)


def comparison_report(repository_root: str | Path | None = None) -> dict[str, Any]:
    """Compare prior provider predictions on identical target/input/taxonomy.

    The report never calls a provider.  A target only contributes when at least
    two providers have successful immutable predictions for the same input and
    taxonomy snapshot.
    """
    root = _root(repository_root)
    groups: dict[tuple[str, str, str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for path in sorted((root / ".research" / "classifications").glob("cls_*.json")):
        record = _load_json(path)
        if not record or record.get("disposition") == "failed":
            continue
        key = tuple(
            str(record.get(field, ""))
            for field in (
                "target_kind",
                "target_id",
                "input_sha256",
                "taxonomy_sha256",
                "question_set_sha256",
            )
        )
        provider = record.get("provider")
        if provider not in {"rules", "jev", "laya"}:
            continue
        old = groups[key].get(provider)
        if old is None or str(record.get("created_at", "")) >= str(old.get("created_at", "")):
            groups[key][provider] = record
    pairs = 0
    category_agree = 0
    tag_agree = 0
    by_pair: Counter[str] = Counter()
    for predictions in groups.values():
        providers = sorted(predictions)
        for index, first in enumerate(providers):
            for second in providers[index + 1 :]:
                pairs += 1
                pair = f"{first}:{second}"
                by_pair[pair] += 1
                left, right = predictions[first], predictions[second]
                left_raw = left.get("answers", {})
                right_raw = right.get("answers", {})
                left_category = left_raw.get("category", {}).get("choice")
                right_category = right_raw.get("category", {}).get("choice")
                category_agree += left_category == right_category
                left_tags = {
                    key.removeprefix("tag_")
                    for key, answer in left_raw.items()
                    if key.startswith("tag_")
                    and isinstance(answer, dict)
                    and isinstance(answer.get("noul"), int | float)
                    and answer["noul"] >= 0.5
                }
                right_tags = {
                    key.removeprefix("tag_")
                    for key, answer in right_raw.items()
                    if key.startswith("tag_")
                    and isinstance(answer, dict)
                    and isinstance(answer.get("noul"), int | float)
                    and answer["noul"] >= 0.5
                }
                tag_agree += left_tags == right_tags
    return {
        "matched_target_pairs": pairs,
        "category_agreement": category_agree / pairs if pairs else None,
        "exact_tag_set_agreement": tag_agree / pairs if pairs else None,
        "by_provider_pair": dict(sorted(by_pair.items())),
        "note": "Agreement is not accuracy; use evaluate_gold with independent human labels for quality metrics.",
    }


def replay_job_health(repository_root: str | Path | None = None) -> dict[str, Any]:
    """Summarize latest immutable replay-manifest versions and integrity errors."""
    root = _root(repository_root)
    directory = _job_dir(root)
    latest: dict[str, Path] = {}
    malformed: list[dict[str, str]] = []
    pattern = re.compile(r"^(crj_[0-9a-f-]+)\.v([0-9]{4})\.json$")
    for path in sorted(directory.glob("crj_*.v*.json")) if directory.exists() else []:
        match = pattern.fullmatch(path.name)
        if not match:
            malformed.append(
                {
                    "path": f".research/{_JOB_DIRECTORY}/{path.name}",
                    "error": "invalid replay-job filename",
                }
            )
            continue
        job_id, version = match.groups()
        previous = latest.get(job_id)
        if previous is None or int(previous.stem.rsplit(".v", 1)[1]) < int(version):
            latest[job_id] = path
    statuses: Counter[str] = Counter()
    target_statuses: Counter[str] = Counter()
    if not latest:
        return {
            "job_count": 0,
            "by_status": {},
            "targets_by_status": {},
            "malformed_count": len(malformed),
            "malformed_records": malformed,
        }
    try:
        registry = registry_for_root(root, allow_package_fallback=True)
    except (OSError, SchemaError) as exc:
        malformed.extend(
            {"path": f".research/{_JOB_DIRECTORY}/{path.name}", "error": str(exc)[:300]}
            for path in latest.values()
        )
        return {
            "job_count": 0,
            "by_status": {},
            "targets_by_status": {},
            "malformed_count": len(malformed),
            "malformed_records": malformed,
        }
    for job_id, path in sorted(latest.items()):
        record = _load_json(path)
        try:
            if not record or record.get("id") != job_id:
                raise ValueError("replay job identity does not match its filename")
            registry.validate("classification-replay-job", record)
        except (ValueError, KeyError, SchemaError, jsonschema.ValidationError) as exc:
            malformed.append(
                {"path": f".research/{_JOB_DIRECTORY}/{path.name}", "error": str(exc)[:300]}
            )
            continue
        statuses[str(record.get("status", "unknown"))] += 1
        target_statuses.update(
            str(target.get("status", "unknown")) for target in record.get("targets", [])
        )
    return {
        "job_count": sum(statuses.values()),
        "by_status": dict(sorted(statuses.items())),
        "targets_by_status": dict(sorted(target_statuses.items())),
        "malformed_count": len(malformed),
        "malformed_records": malformed,
    }


def load_human_gold(path: str | Path) -> list[dict[str, Any]]:
    """Read human-authored JSON Lines labels kept separate from predictions."""
    labels: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            label = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"gold label line {number} is not valid JSON") from exc
        required = {
            "target_kind",
            "target_id",
            "category",
            "tags",
            "label_source",
            "annotator",
            "rubric_id",
            "split",
            "input_sha256",
        }
        if not isinstance(label, dict) or required.difference(label):
            raise ValueError(f"gold label line {number} is missing required human-label fields")
        if (
            label["label_source"] != "human"
            or not isinstance(label["annotator"], str)
            or not label["annotator"].strip()
        ):
            raise ValueError(f"gold label line {number} must declare a named human annotator")
        if label["target_kind"] not in _KINDS or not isinstance(label["target_id"], str):
            raise ValueError(f"gold label line {number} has an invalid target")
        if label["split"] not in {"tuning", "held_out"}:
            raise ValueError(f"gold label line {number} split must be tuning or held_out")
        if not isinstance(label["rubric_id"], str) or not label["rubric_id"].strip():
            raise ValueError(f"gold label line {number} must identify the human-label rubric")
        if not _sha256(label["input_sha256"]):
            raise ValueError(f"gold label line {number} must include its 64-character input_sha256")
        if "taxonomy_sha256" in label and not _sha256(label["taxonomy_sha256"]):
            raise ValueError(
                f"gold label line {number} taxonomy_sha256 must be a 64-character lowercase SHA-256 when supplied"
            )
        if "taxonomy_version" in label and (
            not isinstance(label["taxonomy_version"], str) or not label["taxonomy_version"]
        ):
            raise ValueError(
                f"gold label line {number} taxonomy_version must be a non-empty string when supplied"
            )
        if label["category"] is not None and not isinstance(label["category"], str):
            raise ValueError(f"gold label line {number} category must be a string or null")
        if not isinstance(label["tags"], list) or not all(
            isinstance(tag, str) for tag in label["tags"]
        ):
            raise ValueError(f"gold label line {number} tags must be a list of strings")
        target_key = (label["target_kind"], label["target_id"])
        previous = seen.get(target_key)
        if previous:
            adjudicated = bool(previous.get("adjudicated")) and bool(label.get("adjudicated"))
            same_label = previous["category"] == label["category"] and set(previous["tags"]) == set(
                label["tags"]
            )
            if not adjudicated or not same_label:
                raise ValueError(
                    f"gold label line {number} duplicates {target_key!r}; duplicates require matching adjudicated labels"
                )
            continue
        seen[target_key] = label
        labels.append(label)
    return labels


def _prf(true_positive: int, false_positive: int, false_negative: int) -> dict[str, float]:
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    )
    return {
        "precision": precision,
        "recall": recall,
        "f1": (2 * precision * recall / (precision + recall)) if precision + recall else 0.0,
    }


def _wilson_interval(successes: int, sample_count: int) -> dict[str, float] | None:
    """Two-sided 95% Wilson interval for a binomial estimate."""
    if not sample_count:
        return None
    z = 1.959963984540054
    proportion = successes / sample_count
    denominator = 1 + z * z / sample_count
    centre = (proportion + z * z / (2 * sample_count)) / denominator
    half_width = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / sample_count + z * z / (4 * sample_count * sample_count)
        )
        / denominator
    )
    return {
        "confidence_level": 0.95,
        "lower": max(0.0, centre - half_width),
        "upper": min(1.0, centre + half_width),
    }


def _calibration(values: list[tuple[float, int]]) -> dict[str, Any]:
    """Return Brier/ECE for probabilities tied directly to binary gold labels."""
    if not values:
        return {
            "supported": False,
            "sample_count": 0,
            "reason": "No prediction probabilities map directly to a gold decision.",
        }
    bins: list[list[tuple[float, int]]] = [[] for _ in range(10)]
    for probability, outcome in values:
        bins[min(int(probability * 10), 9)].append((probability, outcome))
    sample_count = len(values)
    ece = 0.0
    breakdown = []
    for index, bucket in enumerate(bins):
        if not bucket:
            continue
        confidence = sum(value for value, _ in bucket) / len(bucket)
        accuracy = sum(outcome for _, outcome in bucket) / len(bucket)
        ece += len(bucket) / sample_count * abs(confidence - accuracy)
        breakdown.append(
            {
                "lower": index / 10,
                "upper": (index + 1) / 10,
                "count": len(bucket),
                "confidence": confidence,
                "accuracy": accuracy,
            }
        )
    return {
        "supported": True,
        "sample_count": sample_count,
        "brier_score": sum((probability - outcome) ** 2 for probability, outcome in values)
        / sample_count,
        "expected_calibration_error": ece,
        "bins": breakdown,
    }


def _metrics(matches: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    labels_seen = sorted(
        {str(label["category"]) for label, _ in matches}
        | {str(prediction.get("category")) for _, prediction in matches}
    )
    category_rows: dict[str, dict[str, Any]] = {}
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    category_calibration: list[tuple[float, int]] = []
    tag_calibration: list[tuple[float, int]] = []
    for label, prediction in matches:
        actual, predicted = str(label["category"]), str(prediction.get("category"))
        confusion[actual][predicted] += 1
        raw_category = prediction.get("answers", {}).get("category", {})
        probabilities = (
            raw_category.get("probabilities", {}) if isinstance(raw_category, dict) else {}
        )
        raw_choice = raw_category.get("choice") if isinstance(raw_category, dict) else None
        if (
            isinstance(probabilities, dict)
            and isinstance(raw_choice, str)
            and isinstance(probabilities.get(raw_choice), int | float)
        ):
            category_calibration.append(
                (float(probabilities[raw_choice]), int(label["category"] == raw_choice))
            )
        probabilities_by_tag = prediction.get("tag_probabilities", {})
        if isinstance(probabilities_by_tag, dict):
            for tag, probability in probabilities_by_tag.items():
                if isinstance(probability, int | float):
                    tag_calibration.append((float(probability), int(tag in label["tags"])))
    for value in labels_seen:
        tp = sum(
            str(label["category"]) == value and str(prediction.get("category")) == value
            for label, prediction in matches
        )
        fp = sum(
            str(label["category"]) != value and str(prediction.get("category")) == value
            for label, prediction in matches
        )
        fn = sum(
            str(label["category"]) == value and str(prediction.get("category")) != value
            for label, prediction in matches
        )
        category_rows[value] = {
            "support": sum(str(label["category"]) == value for label, _ in matches),
            **_prf(tp, fp, fn),
        }
    tag_names = sorted(
        {tag for label, _ in matches for tag in label["tags"]}
        | {tag for _, prediction in matches for tag in prediction.get("proposed_tags", [])}
    )
    tag_rows: dict[str, dict[str, Any]] = {}
    total_tp = total_fp = total_fn = 0
    for tag in tag_names:
        tp = sum(
            tag in label["tags"] and tag in prediction.get("proposed_tags", [])
            for label, prediction in matches
        )
        fp = sum(
            tag not in label["tags"] and tag in prediction.get("proposed_tags", [])
            for label, prediction in matches
        )
        fn = sum(
            tag in label["tags"] and tag not in prediction.get("proposed_tags", [])
            for label, prediction in matches
        )
        total_tp += tp
        total_fp += fp
        total_fn += fn
        tag_rows[tag] = {
            "support": sum(tag in label["tags"] for label, _ in matches),
            **_prf(tp, fp, fn),
        }
    macro_f1 = (
        sum(row["f1"] for row in category_rows.values()) / len(category_rows)
        if category_rows
        else None
    )
    return {
        "sample_count": len(matches),
        "category": {
            "accuracy": sum(
                label["category"] == prediction.get("category") for label, prediction in matches
            )
            / len(matches)
            if matches
            else None,
            "accuracy_wilson_95": _wilson_interval(
                sum(
                    label["category"] == prediction.get("category") for label, prediction in matches
                ),
                len(matches),
            ),
            "macro_f1": macro_f1,
            "per_label": category_rows,
            "confusion_counts": {
                actual: dict(sorted(values.items())) for actual, values in sorted(confusion.items())
            },
            "calibration": _calibration(category_calibration),
        },
        "tags": {
            "micro": _prf(total_tp, total_fp, total_fn),
            "per_tag": tag_rows,
            "calibration": _calibration(tag_calibration),
        },
    }


def evaluate_gold(
    gold: Iterable[dict[str, Any]],
    *,
    repository_root: str | Path | None = None,
    provider: str | None = None,
    split: str = "held_out",
    model: str | None = None,
) -> dict[str, Any]:
    """Evaluate model classifications against independent human gold labels."""
    if split not in {"tuning", "held_out"}:
        raise ValueError("split must be tuning or held_out")
    if provider not in {"rules", "jev", "laya"}:
        raise ValueError("provider must be selected explicitly for benchmark evaluation")
    root = _root(repository_root)
    predictions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for path in sorted((root / ".research" / "classifications").glob("cls_*.json")):
        record = _load_json(path)
        if (
            not record
            or record.get("disposition") == "failed"
            or record.get("provider") != provider
            or (
                model is not None
                and model not in {record.get("requested_model"), record.get("model")}
            )
        ):
            continue
        predictions[(str(record.get("target_kind", "")), str(record.get("target_id", "")))].append(
            record
        )
    settings = {
        (
            record.get("requested_model"),
            record.get("model"),
            record.get("question_set_sha256"),
            record.get("threshold"),
        )
        for records in predictions.values()
        for record in records
    }
    if model is None and len(settings) > 1:
        raise ValueError(
            "model selection is ambiguous; select a model or create a homogeneous replay"
        )
    all_labels = list(gold)
    labels = [label for label in all_labels if label["split"] == split]
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    missing: list[dict[str, str]] = []
    missing_reasons: Counter[str] = Counter()
    for label in labels:
        candidates = predictions.get((label["target_kind"], label["target_id"]), [])
        matching_input = [
            item for item in candidates if item.get("input_sha256") == label["input_sha256"]
        ]
        matching_taxonomy = [
            item
            for item in matching_input
            if (
                "taxonomy_sha256" not in label
                or item.get("taxonomy_sha256") == label["taxonomy_sha256"]
            )
            and (
                "taxonomy_version" not in label
                or item.get("taxonomy_version") == label["taxonomy_version"]
            )
        ]
        if not matching_taxonomy:
            reason = (
                "target_not_classified"
                if not candidates
                else "input_sha256_mismatch"
                if not matching_input
                else "taxonomy_mismatch"
            )
            missing_reasons[reason] += 1
            missing.append(
                {
                    "target_kind": label["target_kind"],
                    "target_id": label["target_id"],
                    "reason": reason,
                }
            )
        else:
            prediction = max(matching_taxonomy, key=lambda item: str(item.get("created_at", "")))
            matches.append((label, prediction))
    metrics = _metrics(matches)
    stratified = {
        kind: _metrics(
            [(label, prediction) for label, prediction in matches if label["target_kind"] == kind]
        )
        for kind in sorted({label["target_kind"] for label in labels})
    }
    return {
        "gold_records": len(labels),
        "excluded_other_split": len(all_labels) - len(labels),
        "labels_without_taxonomy_identity": sum(
            "taxonomy_sha256" not in label or "taxonomy_version" not in label for label in labels
        ),
        "evaluated_records": len(matches),
        "coverage": len(matches) / len(labels) if labels else None,
        "missing_prediction_targets": missing,
        "missing_prediction_counts": dict(sorted(missing_reasons.items())),
        "provider_filter": provider,
        "split": split,
        **metrics,
        "by_target_kind": stratified,
        "note": "Gold labels are accepted only from records explicitly declared as human-authored; predictions are never used as gold. Predictions must match the gold input hash and any supplied taxonomy identity.",
    }


__all__ = [
    "comparison_report",
    "evaluate_gold",
    "evidence_targets",
    "load_human_gold",
    "replay_existing",
    "replay_job_health",
]
