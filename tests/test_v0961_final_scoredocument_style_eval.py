from __future__ import annotations

from evaluation.v0961_final_score_style_integration.run_v0961_eval import run


def test_v0961_final_score_style_eval_runs_with_no_failures() -> None:
    summary = run(max_prompts=2)

    assert summary["failure_count"] == 0
    assert summary["average_final_melody_style_match_rate"] >= 1.0
    assert summary["average_final_harmony_style_match_rate"] >= 0.65
