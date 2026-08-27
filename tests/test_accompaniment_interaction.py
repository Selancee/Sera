from __future__ import annotations

import random

from backend.generation.musicality.accompaniment_interaction import plan_accompaniment_interaction


def test_accompaniment_interaction_reports_cadence_support() -> None:
    report = plan_accompaniment_interaction(
        {"measures": [{"measure": 4, "phrase_end": True}]},
        ["I", "IV", "V", "I"],
        {"style": "classical", "base_style": "classical"},
        {"style": "bass_chord"},
        random.Random(1),
    )

    assert report["melody_supported"] is True
    assert report["cadence_supported"] is True
    assert report["interaction_type"] == "cadence_support"
