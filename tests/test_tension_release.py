from __future__ import annotations

import random

from backend.generation.musicality.tension_release import plan_tension_release_curve, score_tension_release


def test_tension_release_curve_rewards_cadential_release() -> None:
    curve = plan_tension_release_curve("final", ["I", "IV", "V", "I"], {}, {"style": "classical"}, random.Random(1))
    events = [
        {"type": "note", "midi": 62, "measure": 1, "duration": 0.5},
        {"type": "note", "midi": 72, "measure": 2, "duration": 0.5},
        {"type": "note", "midi": 67, "measure": 3, "duration": 1.0},
        {"type": "note", "midi": 60, "measure": 4, "duration": 2.0},
    ]
    report = score_tension_release(events, ["I", "IV", "V", "I"], curve)

    assert curve["planned_curve"][-1] < curve["planned_curve"][1]
    assert report["cadence_release_score"] >= 0.45
