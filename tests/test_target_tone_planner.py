from __future__ import annotations

from backend.generation.musicality.target_tone_planner import plan_target_tones, target_tone_hit_report


def test_target_tone_planner_requires_phrase_end_targets() -> None:
    targets = plan_target_tones(["ii7", "V7", "Imaj7", "Imaj7"], "final", {"style": "jazz", "base_style": "jazz", "key": "F major"}, {"style_family": "jazz"})
    events = [
        {"type": "note", "midi": 69, "measure": 1, "offset": 0.0},
        {"type": "note", "midi": 69, "measure": 4, "offset": 3.0, "phrase_end": True},
    ]
    report = target_tone_hit_report(events, targets)

    assert targets[-1]["required"] is True
    assert "cadence" in targets[-1]["target_type"]
    assert report["required_target_tone_hit_rate"] >= 0.5
