from backend.services.score_document_service import new_score_document, score_document_to_musicxml
from backend.services.score_preview_render_service import ScorePreviewRenderService


def test_preview_render_service_returns_structured_result(tmp_path) -> None:
    score = new_score_document(measures=1)
    musicxml = score_document_to_musicxml(score)

    result = ScorePreviewRenderService(tmp_path).render_musicxml(musicxml, "svg", render_id="test_preview")

    assert "success" in result
    assert result["renderer"] in {"musescore_cli", "verovio", "unavailable"}
    assert "svg_url" in result
    assert result["musicxml_text_available"] is True


def test_renderer_status_reports_backend_preview_availability(tmp_path) -> None:
    status = ScorePreviewRenderService(tmp_path).renderer_status()

    assert "musescore_available" in status
    assert "verovio_available" in status
    assert "backend_svg_supported" in status
    assert "install_hints" in status
