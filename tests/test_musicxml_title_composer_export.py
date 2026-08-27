from backend.services.score_document_service import musicxml_to_score_document, new_score_document, score_document_to_musicxml
from backend.services.score_operation_service import apply_score_operation


def test_musicxml_export_uses_score_document_title_and_composer() -> None:
    score = new_score_document(title="Cyberpunk Piano Study", composer="selance", key="A minor", measures=1)
    musicxml = score_document_to_musicxml(score)

    assert "<work-title>Cyberpunk Piano Study</work-title>" in musicxml
    assert '<creator type="composer">selance</creator>' in musicxml


def test_title_and_composer_edits_survive_musicxml_export() -> None:
    score = new_score_document(measures=1)
    score, _ = apply_score_operation(score, {"source": "user", "type": "change_title", "target": {"field": "title"}, "after": {"title": "Edited Title"}, "description": "Change title"})
    score, _ = apply_score_operation(score, {"source": "user", "type": "change_composer", "target": {"field": "composer"}, "after": {"composer": "Edited Composer"}, "description": "Change composer"})
    exported = score_document_to_musicxml(score)
    imported = musicxml_to_score_document(exported)

    assert "<work-title>Edited Title</work-title>" in exported
    assert '<creator type="composer">Edited Composer</creator>' in exported
    assert imported["title"] == "Edited Title"
    assert imported["composer"] == "Edited Composer"

