from training.tasks.cadence_generation_task import build_cadence_generation_examples


def test_cadence_generation_task_shape() -> None:
    events = ["KEY_C_MAJOR", "BAR", "NOTE_D5", "NOTE_B4", "NOTE_G4", "NOTE_C5", "CADENCE_AUTHENTIC", "END"]
    examples = build_cadence_generation_examples(events)
    assert examples[0]["task_type"] == "cadence_generation"
    assert examples[0]["input_tokens"][0] == "TASK_CADENCE"
    assert examples[0]["target_tokens"][-1] == "NOTE_C5"
