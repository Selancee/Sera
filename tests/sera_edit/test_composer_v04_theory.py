"""Composer V0.4 expectation, texture, and trace regressions."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app
from sera_edit.composer.pipeline import compose_with_runtime, generate_composition_candidates
from sera_edit.composer.run_trace import ComposerRunTraceStore
from sera_edit.composer.texture_analysis import analyze_texture


def test_texture_analysis_distinguishes_monophony_and_homorhythm(two_staff_score: dict) -> None:
    before = json.dumps(two_staff_score, ensure_ascii=False, sort_keys=True)
    chordal = analyze_texture(two_staff_score, {"measures": [1, 2]})
    assert chordal["texture"] == "homorhythmic_chordal"
    assert chordal["voice_count"] == 2
    assert chordal["attack_alignment_ratio"] == 1.0

    monophonic = deepcopy(two_staff_score)
    for measure in monophonic["measures"]:
        measure["events"] = [event for event in measure["events"] if event["staff"] == "right_hand"]
    monophonic["tracks"] = [track for track in monophonic["tracks"] if track["staff"] == "right_hand"]
    mono = analyze_texture(monophonic, {"measures": [1, 2]})
    assert mono["texture"] == "monophonic"
    assert mono["confidence"] >= 0.95
    assert json.dumps(two_staff_score, ensure_ascii=False, sort_keys=True) == before


def test_composer_reviews_candidates_with_expectation_and_texture_evidence(two_staff_score: dict) -> None:
    result = generate_composition_candidates(
        two_staff_score,
        "依据旋律期待改写为清晰的古典乐句，保留织体和节奏",
        {"measures": [1, 2]},
        {},
        candidate_count=3,
        search_width=8,
    )
    assert result["status"] == "generated"
    assert result["texture_analysis"]["texture"] == "homorhythmic_chordal"
    assert result["style_knowledge"]["query"]["source_texture"] == "homorhythmic_chordal"
    for candidate in result["candidates"]:
        review = candidate["review"]
        assert 0.0 <= review["melody_expectation_score"] <= 1.0
        assert review["melody_expectation_report"]["model_family"] == "huron_tessitura_expectation_proxy_v1"
        assert review["texture_structure_preserved"] is True
        checks = {finding["check"] for finding in review["findings"]}
        assert {"melodic_expectation", "texture_structure_preserved"}.issubset(checks)


def test_composer_local_trace_proves_planner_source_without_score_notes(two_staff_score: dict) -> None:
    result = compose_with_runtime(
        two_staff_score,
        "写一个有清晰终止的古典旋律变奏",
        {"measures": [1, 2]},
        {},
        use_live_planner=False,
    )
    assert result["planner"]["planner"] == "deterministic_theory"
    assert result["run_trace"]["persisted"] is True
    trace_path = Path(os.environ["SERA_COMPOSER_TRACE_FILE"])
    raw = trace_path.read_text(encoding="utf-8")
    assert '"pitch"' not in raw
    latest = ComposerRunTraceStore(trace_path).latest()
    assert latest is not None
    assert latest["result"]["planner"]["planner"] == "deterministic_theory"
    assert latest["result"]["texture_analysis"]["texture"] == "homorhythmic_chordal"
    assert latest["privacy"]["stores_note_or_event_content"] is False

    response = TestClient(app).get("/sera-edit/composer/latest-run")
    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["trace"]["trace_id"] == latest["trace_id"]
