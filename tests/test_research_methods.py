"""Protocol-first research-method contracts and completion gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from polder_research import evidence as evidence_module
from polder_research import paths as paths_module
from polder_research import research_methods as methods
from polder_research import runs as runs_module


@pytest.fixture
def method_repo(monkeypatch, tmp_path: Path):
    research = tmp_path / ".research"
    dirs = {
        "RESEARCH_RUNS_DIR": research / "runs",
        "RESEARCH_PROTOCOLS_DIR": research / "protocols",
        "RESEARCH_SEARCHES_DIR": research / "searches",
        "RESEARCH_CANDIDATES_DIR": research / "candidates",
        "RESEARCH_SCREENINGS_DIR": research / "screenings",
        "RESEARCH_APPRAISALS_DIR": research / "appraisals",
        "RESEARCH_EXTRACTIONS_DIR": research / "extractions",
        "RESEARCH_REPORTS_DIR": research / "reports",
        "EVIDENCE_SOURCES_DIR": research / "sources",
        "EVIDENCE_SEGMENTS_DIR": research / "segments",
    }
    for module in (paths_module, runs_module, methods, evidence_module):
        for name, value in dirs.items():
            monkeypatch.setattr(module, name, value, raising=False)
    monkeypatch.setattr(methods, "REPO_ROOT", tmp_path)

    question = "How do realtime image models compare on latency and visual quality?"
    run_id = runs_module.write_run(
        brief={"question": question, "scope": "Realtime visual platform research"},
        research_method="systematic_evidence_review",
    )
    protocol_id = methods.create_protocol(
        run_id,
        {
            "question": question,
            "objectives": ["Compare supported latency and quality evidence."],
            "questions": [question],
            "framework": "custom",
            "eligibility": {
                "inclusion": ["Reports a realtime image model or platform evaluation."],
                "exclusion": ["No relevant model or platform evidence."],
                "languages": ["en"],
            },
            "search_plan": {
                "cutoff_at": "2026-09-24T00:00:00Z",
                "queries": [
                    {
                        "id": "web-search-1",
                        "database": "Web search",
                        "platform": "Example Search",
                        "query": '"realtime image generation" latency benchmark',
                        "language": "en",
                        "limits": ["English"],
                    }
                ],
            },
            "screening_plan": {
                "reviewers": [
                    {"id": "reviewer-a", "kind": "human", "independence_group": "person-a"},
                    {"id": "reviewer-b", "kind": "human", "independence_group": "person-b"},
                ],
                "adjudicator": {"id": "adjudicator", "kind": "human"},
                "adjudication_rule": "Independent reviewers discuss discrepancies; adjudicator records resolution.",
                "exclusion_reasons": ["irrelevant", "no full text", "duplicate"],
            },
            "extraction_plan": {
                "fields": ["model", "latency", "quality", "evaluation conditions"],
                "duplicate_review": True,
            },
            "appraisal_plan": {
                "required": True,
                "instrument": "technical-evidence-appraisal-v1",
                "instrument_version": "1",
                "instrument_reference": "https://example.org/methods/technical-evidence-appraisal-v1",
                "rationale": "Use domain-specific judgments for benchmark and platform evidence.",
            },
            "synthesis_plan": {
                "method": "narrative",
                "grouping": "Group by model, modality, and evaluation setup.",
                "heterogeneity": "Report incompatible setups separately.",
                "sensitivity_analysis": "Repeat synthesis excluding vendor-only evidence.",
                "certainty_framework": "Qualitative certainty with explicit rationale; no pooled score.",
            },
        },
        created_by="curator",
    )
    digest = methods.freeze_protocol(protocol_id)
    return {"root": tmp_path, "run_id": run_id, "protocol_id": protocol_id, "digest": digest}


def _active(method_repo: dict[str, str]) -> str:
    runs_module.update_run_status(method_repo["run_id"], "active")
    return method_repo["run_id"]


def _saved_export(method_repo: dict[str, str], content: bytes) -> tuple[str, str]:
    path = method_repo["root"] / "raw" / "search-results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return "raw/search-results.json", hashlib.sha256(content).hexdigest()


def test_systematic_run_cannot_activate_without_frozen_protocol(monkeypatch, tmp_path):
    research = tmp_path / ".research"
    (research / "runs").mkdir(parents=True)
    monkeypatch.setattr(runs_module, "RESEARCH_RUNS_DIR", research / "runs")
    monkeypatch.setattr(methods, "RESEARCH_RUNS_DIR", research / "runs")
    run_id = runs_module.write_run(
        {"question": "A question"}, research_method="systematic_evidence_review"
    )
    with pytest.raises(ValueError, match="no frozen protocol"):
        runs_module.update_run_status(run_id, "active")


def test_protocol_freeze_binds_run_and_detects_tampering(method_repo):
    run = method_repo["run_id"]
    assert methods.verify_run_protocol(run)[1]["content_sha256"] == method_repo["digest"]
    protocol_path = Path(methods.RESEARCH_PROTOCOLS_DIR) / f"{method_repo['protocol_id']}.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["questions"] = ["changed after freeze"]
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    with pytest.raises(methods.ResearchMethodError, match="hash mismatch"):
        methods.verify_run_protocol(run)


def test_search_candidate_dedup_screening_and_appraisal(method_repo):
    run_id = _active(method_repo)
    export_location, export_sha256 = _saved_export(method_repo, b'{"results": [1, 2]}')
    search_id = methods.record_search(
        run_id,
        query_id="web-search-1",
        executed_by="researcher",
        executed_at="2026-09-24T08:00:00Z",
        result_count=2,
        export_sha256=export_sha256,
        export_location=export_location,
        tool_name="browser",
        tool_version="1.0",
    )
    candidate_id = methods.register_candidate(
        run_id,
        search_id=search_id,
        title="Realtime image generation latency benchmark",
        stable_identifiers=["doi:10.1234/visual.1"],
        url="https://example.org/paper",
        abstract="A benchmark report.",
    )
    duplicate_id = methods.register_candidate(
        run_id,
        search_id=search_id,
        title="Different title for same report",
        stable_identifiers=["doi:10.1234/visual.1"],
    )
    candidate = json.loads(
        (Path(methods.RESEARCH_CANDIDATES_DIR) / f"{duplicate_id}.json").read_text()
    )
    assert candidate["status"] == "duplicate"
    assert candidate["duplicate_of"] == candidate_id

    for reviewer in ("reviewer-a", "reviewer-b"):
        methods.record_screening_decision(
            run_id,
            candidate_id=candidate_id,
            stage="title_abstract",
            reviewer_id=reviewer,
            outcome="include",
            rationale="Meets the prespecified scope.",
        )
    source_id = evidence_module.register_source(
        title="Realtime image generation latency benchmark",
        source_type="paper",
        media_type="pdf",
        raw_bytes=b"captured full text",
        repository_root=Path(methods.EVIDENCE_SOURCES_DIR).parents[1],
    )
    segment_id = evidence_module.register_segment(
        source_id=source_id,
        text="Observed end-to-end latency was 300 ms in the tested configuration.",
        locator_scheme="page",
        locator_value="4",
        repository_root=Path(methods.EVIDENCE_SOURCES_DIR).parents[1],
    )
    for reviewer in ("reviewer-a", "reviewer-b"):
        methods.record_screening_decision(
            run_id,
            candidate_id=candidate_id,
            stage="full_text",
            reviewer_id=reviewer,
            outcome="include",
            rationale="The full text meets all inclusion criteria.",
            source_id=source_id,
        )
    methods.record_appraisal(
        run_id,
        candidate_id=candidate_id,
        source_id=source_id,
        reviewer_id="reviewer-a",
        instrument="technical-evidence-appraisal-v1",
        overall_judgement="some concerns",
        domains=[
            {
                "name": "measurement validity",
                "judgement": "some concerns",
                "rationale": "Device details are incomplete.",
            },
            {
                "name": "independence",
                "judgement": "high concerns",
                "rationale": "Vendor funded the comparison.",
            },
        ],
        limitations=["Single device configuration."],
    )
    for field in ("model", "latency", "quality", "evaluation conditions"):
        for reviewer in ("reviewer-a", "reviewer-b"):
            methods.record_extraction(
                run_id,
                candidate_id=candidate_id,
                source_id=source_id,
                reviewer_id=reviewer,
                field=field,
                status="reported",
                rationale="Copied from the cited source passage.",
                value=("250 ms" if field == "latency" and reviewer == "reviewer-a" else "350 ms")
                if field == "latency"
                else f"reported {field}",
                segment_id=segment_id,
            )
        if field == "latency":
            methods.adjudicate_extraction(
                run_id,
                candidate_id=candidate_id,
                source_id=source_id,
                field=field,
                adjudicator_id="adjudicator",
                status="reported",
                rationale="The source context reports the median of the two tested runs.",
                value="300 ms",
                segment_id=segment_id,
            )
    flow = methods.screening_flow(run_id)
    assert flow["records_identified"] == 2
    assert flow["duplicates_removed"] == 1
    assert flow["studies_included"] == 1
    assert flow["extraction_fields_required"] == flow["extraction_fields_resolved"] == 4
    assert methods.validate_run_for_completion(run_id) == [
        "review audit report has not been generated"
    ]
    report = methods.generate_review_report(
        run_id, limitations=["Search coverage is bounded to the recorded sources."]
    )
    assert report.is_file()
    assert methods.validate_run_for_completion(run_id) == []
    runs_module.update_run_status(run_id, "completed")


def test_disagreement_requires_independent_human_adjudication(method_repo):
    run_id = _active(method_repo)
    export_location, export_sha256 = _saved_export(method_repo, b'{"results": [1]}')
    search_id = methods.record_search(
        run_id,
        query_id="web-search-1",
        executed_by="researcher",
        executed_at="2026-09-24T08:00:00Z",
        result_count=1,
        export_sha256=export_sha256,
        export_location=export_location,
    )
    candidate_id = methods.register_candidate(
        run_id, search_id=search_id, title="Possibly relevant benchmark"
    )
    first = methods.record_screening_decision(
        run_id,
        candidate_id=candidate_id,
        stage="title_abstract",
        reviewer_id="reviewer-a",
        outcome="include",
        rationale="Potentially in scope.",
    )
    second = methods.record_screening_decision(
        run_id,
        candidate_id=candidate_id,
        stage="title_abstract",
        reviewer_id="reviewer-b",
        outcome="exclude",
        rationale="Appears out of scope.",
        exclusion_reason="irrelevant",
    )
    with pytest.raises(methods.ResearchMethodError, match="does not match"):
        methods.adjudicate_screening(
            run_id,
            candidate_id=candidate_id,
            stage="title_abstract",
            outcome="include",
            adjudicator_id="reviewer-a",
            rationale="Not an authorized adjudicator.",
        )
    adjudication_id = methods.adjudicate_screening(
        run_id,
        candidate_id=candidate_id,
        stage="title_abstract",
        outcome="include",
        adjudicator_id="adjudicator",
        rationale="The abstract satisfies the scope.",
    )
    adjudication = json.loads(
        (Path(methods.RESEARCH_SCREENINGS_DIR) / f"{adjudication_id}.json").read_text()
    )
    assert set(adjudication["resolves_decision_ids"]) == {first, second}
    assert methods.screening_flow(run_id)["unresolved_decisions"] == 0
