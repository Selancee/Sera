from training.tokenization.structured_events import note_token, transpose_pitch_token
from training.tokenization.structured_tokenizer import StructuredTokenizer


def test_structured_note_and_transpose_tokens() -> None:
    assert note_token("C4") == "NOTE_C4"
    assert transpose_pitch_token("NOTE_C4", 2) == "NOTE_D4"


def test_structured_tokenizer_roundtrip() -> None:
    tokenizer = StructuredTokenizer()
    tokenizer.fit([{"events": ["BAR", "RHYTHM_QUARTER", "NOTE_C4", "END"]}])
    ids = tokenizer.encode(["BAR", "NOTE_C4"])
    assert tokenizer.decode(ids) == ["BAR", "NOTE_C4"]
