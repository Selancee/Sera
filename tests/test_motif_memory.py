from __future__ import annotations

import random

from backend.generation.musicality.motif_memory import create_motif_memory, develop_motif, retrieve_motif, summarize_motif_memory


def test_motif_memory_recalls_and_develops_primary_motif() -> None:
    rng = random.Random(12)
    memory = create_motif_memory([0, 2, 4, 7], {"style": "classical"})
    retrieved = retrieve_motif(memory, "consequent", rng)
    developed = develop_motif(retrieved["motif"], "answer_phrase", {"style": "classical"}, rng)

    assert retrieved["motif_id"] == "primary"
    assert developed != retrieved["motif"]
    report = summarize_motif_memory(
        memory,
        [
            {"motif": retrieved["motif"], "motif_transform": "repeat"},
            {"motif": developed, "motif_transform": "answer_phrase"},
        ],
    )
    assert report["motif_recurrence_count"] >= 1
    assert "answer_phrase" in report["motif_variation_types"]
