from __future__ import annotations

from v0962_phrase_helpers import period_for_style


def test_jazz_phrase_hits_guide_tones_and_uses_approach_color() -> None:
    result = period_for_style("jazz")
    reports = [phrase["jazz_phrase_report"] for phrase in result["phrases"]]

    assert result["style_family"] == "jazz"
    assert max(report["guide_tone_hit_rate"] for report in reports) >= 0.45
    assert sum(report["approach_tone_count"] for report in reports) >= 1
