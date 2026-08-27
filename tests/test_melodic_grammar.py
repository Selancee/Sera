from backend.generation.musicality.melodic_grammar import repair_melodic_line, validate_melodic_line


def test_melodic_grammar_detects_tritone_like_leap() -> None:
    report = validate_melodic_line([60, 66, 67], "C major", "major", {"pitch_vocabulary": "diatonic"}, "intermediate")

    assert not report["valid"]
    assert report["tritone_violation_rate"] > 0


def test_melodic_grammar_repairs_tritone_like_leap() -> None:
    style = {"pitch_vocabulary": "diatonic"}
    repaired = repair_melodic_line([60, 66, 67], "C major", "major", style, "intermediate")
    report = validate_melodic_line(repaired, "C major", "major", style, "intermediate")

    assert report["tritone_violation_rate"] == 0
    assert report["valid"]


def test_pentatonic_repair_snaps_to_chinese_collection() -> None:
    repaired = repair_melodic_line([60, 65, 71], "C major", "major", {"pitch_vocabulary": "pentatonic"}, "intermediate")
    pitch_classes = {note % 12 for note in repaired}

    assert pitch_classes.issubset({0, 2, 4, 7, 9})
