from __future__ import annotations

from v0962_phrase_helpers import period_for_style


def test_classical_phrase_has_periodic_cadential_behavior() -> None:
    result = period_for_style("classical")
    reports = [phrase["classical_phrase_report"] for phrase in result["phrases"]]

    assert result["style_family"] == "classical"
    assert result["phrases"][0]["phrase_role"] == "antecedent"
    assert result["phrases"][1]["phrase_role"] == "final"
    assert min(report["period_balance_score"] for report in reports) >= 0.9
    assert max(report["cadence_preparation_score"] for report in reports) >= 0.5
