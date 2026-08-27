from __future__ import annotations

from v0962_phrase_helpers import period_for_style


def test_romantic_phrase_uses_longer_line_arc() -> None:
    result = period_for_style("romantic")
    reports = [phrase["romantic_phrase_report"] for phrase in result["phrases"]]

    assert result["style_family"] == "romantic"
    assert max(report["long_line_score"] for report in reports) >= 0.75
    assert max(report["phrase_arc_score"] for report in reports) >= 0.45
