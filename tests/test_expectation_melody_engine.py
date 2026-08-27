import random

from backend.generation.musicality.expectation_melody_engine import generate_expectation_melody, repair_melody_by_expectation


def test_expectation_melody_engine_generates_valid_report() -> None:
    result = generate_expectation_melody(
        {"key": "C major", "note_count": 8},
        ["I", "V", "I"],
        {"style": "classical", "key": "C major"},
        {},
        random.Random(7),
    )

    assert result["melody_events"]
    assert result["melody_expectation_report"]["closure_score"] > 0.5


def test_expectation_repair_adds_gap_fill_after_large_leap() -> None:
    result = repair_melody_by_expectation(
        [{"type": "note", "midi": 60}, {"type": "note", "midi": 72}, {"type": "note", "midi": 79}],
        [],
        {"key": "C major"},
    )

    assert "gap_fill_after_large_leap" in result["melody_expectation_report"]["repairs_applied"]
