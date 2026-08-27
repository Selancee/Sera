from backend.generation.musicality.melody_candidate_ranker import rank_melody_candidates


def test_melody_candidate_ranker_rejects_poor_closure() -> None:
    good = [{"type": "note", "midi": 60}, {"type": "note", "midi": 67}, {"type": "note", "midi": 65}, {"type": "note", "midi": 60, "duration": "quarter"}]
    bad = [{"type": "note", "midi": 60}, {"type": "note", "midi": 66}, {"type": "note", "midi": 73}]

    ranked = rank_melody_candidates([bad, good], key="C major")

    assert ranked["selected_candidate_index"] == 1
    assert ranked["rejected_melody_candidates"]
