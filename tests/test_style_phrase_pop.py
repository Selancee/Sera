from __future__ import annotations

from v0962_phrase_helpers import period_for_style


def test_pop_phrase_contains_hook_cell_with_variation() -> None:
    result = period_for_style("pop")
    reports = [phrase["pop_phrase_report"] for phrase in result["phrases"]]

    assert result["style_family"] == "pop"
    assert any(report["hook_cell"] for report in reports)
    assert max(report["hook_variation_count"] for report in reports) >= 1
    assert min(report["singability_score"] for report in reports) >= 0.75
