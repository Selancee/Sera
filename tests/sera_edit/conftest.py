"""Deterministic ScoreDocument fixtures for SeraEdit tests."""

from __future__ import annotations

import pytest

from backend.services.score_document_service import new_score_document, normalize_score_document


@pytest.fixture(autouse=True)
def _isolate_composer_trace(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep Composer audit writes inside each test's temporary directory."""

    monkeypatch.setenv("SERA_COMPOSER_TRACE_FILE", str(tmp_path / "composer_runs.v0.4.jsonl"))


@pytest.fixture
def two_staff_score() -> dict:
    score = new_score_document(title="SeraEdit Fixture", measures=2)
    score["score_id"] = "score_fixture_001"
    pitches = {
        "right_hand": ["C4", "D4", "E4", "F4"],
        "left_hand": ["C3", "G2", "A2", "F2"],
    }
    for measure_number, measure in enumerate(score["measures"], start=1):
        for staff, staff_pitches in pitches.items():
            prefix = "rh" if staff == "right_hand" else "lh"
            for offset, pitch in enumerate(staff_pitches):
                measure["events"].append(
                    {
                        "event_id": f"m{measure_number}_{prefix}_{offset + 1}",
                        "type": "note",
                        "pitch": pitch,
                        "duration": "quarter",
                        "offset": float(offset),
                        "voice": 1,
                        "staff": staff,
                        "tie": None,
                        "slur": None,
                        "accidental": "",
                        "dynamic": "mf",
                        "articulations": [],
                        "selected": False,
                    }
                )
    return normalize_score_document(score)
