from __future__ import annotations

from v0962_phrase_helpers import period_for_style


def test_phrase_melody_engine_generates_four_measure_phrases() -> None:
    result = period_for_style("classical")

    assert result["engine"] == "phrase_melody_engine_v0962"
    assert result["source"] == "phrase_melody_engine"
    assert result["hardcoded_shape_fallback_used"] is False
    assert len(result["phrases"]) == 2
    assert all(phrase["phrase_length_measures"] == 4 for phrase in result["phrases"])
    assert len(result["measures"]) == 8
    assert result["phrase_level_scores"]["motif_development_score"] > 0.0


def test_period_generator_has_antecedent_consequent_relation() -> None:
    result = period_for_style("classical")
    roles = [phrase["phrase_role"] for phrase in result["phrases"]]

    assert roles == ["antecedent", "final"]
    assert result["phrases"][0]["call_response_role"] == "call"
    assert result["phrases"][1]["call_response_role"] == "answer"


def test_phrase_melody_uses_final_score_events_not_only_metadata() -> None:
    result = period_for_style("pop")
    event_midis = [event["midi"] for event in result["melody_events"]]
    measure_midis = [midi for measure in result["measures"] for midi in measure["midis"]]

    assert event_midis == measure_midis
    assert max(event_midis) - min(event_midis) >= 7
