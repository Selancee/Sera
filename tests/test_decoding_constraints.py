from backend.generation.decoding import DecodingConfig, enforce_decoding_constraints, filter_token_candidates


def test_decoding_blocks_excessive_same_duration() -> None:
    history = ["RHYTHM_QUARTER", "RHYTHM_QUARTER", "RHYTHM_QUARTER"]
    candidates = {"RHYTHM_QUARTER": 2.0, "RHYTHM_EIGHTH": 1.0}
    adjusted = filter_token_candidates(candidates, history, DecodingConfig(max_consecutive_same_duration=3))
    assert adjusted["RHYTHM_QUARTER"] == float("-inf")


def test_enforce_decoding_constraints_rewrites_duration_run() -> None:
    output = enforce_decoding_constraints(["RHYTHM_QUARTER"] * 5, DecodingConfig(max_consecutive_same_duration=3))
    assert max(_runs(output, "RHYTHM_QUARTER")) <= 3


def _runs(tokens: list[str], target: str) -> list[int]:
    runs = []
    current = 0
    for token in tokens:
        if token == target:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs or [0]
