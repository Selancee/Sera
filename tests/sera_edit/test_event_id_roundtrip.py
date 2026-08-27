from __future__ import annotations

from backend.services.score_document_service import musicxml_to_score_document, score_document_to_musicxml


def test_sera_event_ids_survive_musicxml_roundtrip(two_staff_score: dict) -> None:
    musicxml = score_document_to_musicxml(two_staff_score)
    imported = musicxml_to_score_document(musicxml)
    source_ids = {
        event["event_id"]
        for measure in two_staff_score["measures"]
        for event in measure["events"]
    }
    imported_ids = {
        event["event_id"]
        for measure in imported["measures"]
        for event in measure["events"]
    }
    assert source_ids <= imported_ids


def test_external_musicxml_without_sera_metadata_gets_stable_local_ids() -> None:
    musicxml = """<?xml version="1.0"?><score-partwise version="3.1"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>whole</type><staff>1</staff></note></measure></part></score-partwise>"""
    imported = musicxml_to_score_document(musicxml)
    assert imported["measures"][0]["events"][0]["event_id"] == "m1_e1"
