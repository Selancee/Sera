from types import SimpleNamespace

from backend.generation.candidate_ranker import CandidateRanker
from backend.models.schemas import ValidationResult


def _candidate(index: int, expectation: float, harmony: float = 0.8) -> dict:
    generated = SimpleNamespace(
        metadata={
            "melody_expectation_report": {"melody_expectation_score": expectation},
            "voice_leading_report": {"style_harmony_match_score": harmony},
            "musicality_validation_report": {"left_hand_activity": 1.0},
            "role_coverage_report": {"lead_melody": True, "harmony": True, "bass": True},
        },
        score_document={"measures": [{"number": 1, "events": [{"pitch": f"C{index + 4}", "duration": "quarter", "offset": 0, "staff": "right_hand", "voice": 1}]}]},
    )
    return {"candidate_index": index, "candidate_seed": index + 10, "parent_run_seed": 99, "generated": generated, "validation": ValidationResult(valid=True)}


def test_candidate_ranker_prefers_expectation_and_harmony_scores() -> None:
    ranked = CandidateRanker().rank([_candidate(0, 0.55), _candidate(1, 0.9, harmony=0.95), _candidate(2, 0.7)])

    assert ranked["candidate_generation"]["selected_candidate_index"] == 1
    assert ranked["candidate_generation"]["selected_candidate_metrics"]["melody_expectation_score"] == 0.9
    assert len(ranked["candidate_generation"]["rejected_candidates"]) == 2
