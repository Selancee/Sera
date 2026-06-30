from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.generation.rule_based_generator import RuleBasedGenerator
from backend.models.schemas import StructuredMusicIntent
from training.tokenization.musicxml_to_structured_events import musicxml_to_structured_events


def test_musicxml_to_structured_events_contains_separate_pitch_and_rhythm() -> None:
    plan = CompositionPlanningAgent().plan(StructuredMusicIntent(prompt="8 bar C major piano", bars=8))
    score = RuleBasedGenerator().generate(plan)
    sequence = musicxml_to_structured_events(score.musicxml)

    assert "BAR" in sequence.events
    assert any(token.startswith("RHYTHM_") for token in sequence.events)
    assert any(token.startswith("NOTE_") for token in sequence.events)
    assert not any(token.startswith("NOTE_C4_QUARTER") for token in sequence.events)
