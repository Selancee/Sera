from __future__ import annotations

from v0962_phrase_helpers import period_for_style


def test_cyberpunk_phrase_uses_short_modal_cells() -> None:
    result = period_for_style("cyberpunk")
    reports = [phrase["cyberpunk_phrase_report"] for phrase in result["phrases"]]

    assert result["style_family"] == "cyberpunk"
    assert max(report["short_cell_repetition_score"] for report in reports) >= 0.25
    assert min(report["modal_pitch_rate"] for report in reports) >= 0.75
