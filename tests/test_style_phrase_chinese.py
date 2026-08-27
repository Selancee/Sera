from __future__ import annotations

from v0962_phrase_helpers import period_for_style


def test_chinese_phrase_uses_pentatonic_open_space() -> None:
    result = period_for_style("chinese")
    reports = [phrase["chinese_phrase_report"] for phrase in result["phrases"]]

    assert result["style_family"] == "chinese"
    assert min(report["pentatonic_note_rate"] for report in reports) >= 0.9
    assert max(report["open_space_contour_score"] for report in reports) >= 0.8
