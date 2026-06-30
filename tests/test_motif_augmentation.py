from training.augmentation.motif_augmentation import augment_motif_events


def test_motif_augmentation_sequence_up_changes_notes() -> None:
    events = ["NOTE_C4", "NOTE_D4", "NOTE_E4", "NOTE_G4"]
    output, meta = augment_motif_events(events, "sequence_up")
    assert meta["changed_notes"] > 0
    assert output[0] == "NOTE_D4"
