from backend.generation.rule_based_generator import RuleBasedGenerator
from backend.agents.prompt_understanding_agent import PromptUnderstandingAgent
from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.services.score_consistency_service import ScoreConsistencyService
from backend.services.score_document_service import musicxml_to_score_document, score_document_to_note_events


def test_score_consistency_report_matches_canonical_score_document():
    intent = PromptUnderstandingAgent().understand("Compose a short 8 measure piano piece.")
    plan = CompositionPlanningAgent().plan(intent)
    generated = RuleBasedGenerator().generate(plan)
    score_document = musicxml_to_score_document(generated.musicxml, prompt=intent.prompt, source="generated")
    note_events = score_document_to_note_events(score_document)

    report = ScoreConsistencyService().build_report(
        musicxml=generated.musicxml,
        score_document=score_document,
        midi_note_events=note_events,
    )

    assert report["score_document_event_count"] > 0
    assert report["musicxml_event_count"] > 0
    assert report["measure_count_score_document"] == report["measure_count_musicxml"]
    assert report["note_event_count"] == report["midi_event_count"]
