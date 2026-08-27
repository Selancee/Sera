from evaluation.analysis.music_statistics import parse_musicxml_notes

from backend.pipeline import SeraPipeline


def test_generated_musicxml_contains_real_notes_and_left_hand(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate("Compose an 8 measure cinematic piano theme.", generator_mode="rule_based")
    notes = parse_musicxml_notes(result["musicxml"])

    assert notes
    assert any(str(note.staff) == "2" for note in notes)
    assert result["validation"]["valid"] is True
