from __future__ import annotations

import random

from backend.generation.musicality.phrase_contour import plan_phrase_contour, score_phrase_contour


def test_phrase_contour_plans_register_shape_and_scores_actual_melody() -> None:
    contour = plan_phrase_contour("antecedent", {"style": "romantic"}, {"style_family": "romantic"}, 4, random.Random(1))
    events = [
        {"type": "note", "midi": 60, "measure": 1},
        {"type": "note", "midi": 64, "measure": 2},
        {"type": "note", "midi": 70, "measure": 3},
        {"type": "note", "midi": 65, "measure": 4},
    ]

    assert contour["contour_type"] == "long_romantic_arc"
    assert len(contour["register_points"]) == 4
    assert score_phrase_contour(events, contour)["phrase_contour_score"] > 0.5
