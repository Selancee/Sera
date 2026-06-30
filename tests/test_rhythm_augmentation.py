from training.augmentation.rhythm_augmentation import augment_rhythm_events


def test_rhythm_augmentation_replaces_quarter_run() -> None:
    events = ["RHYTHM_QUARTER"] * 6
    output, meta = augment_rhythm_events(events)
    assert meta["replacements"] > 0
    assert output != events
    assert "RHYTHM_EIGHTH" in output
