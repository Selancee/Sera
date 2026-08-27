import os

from fastapi.testclient import TestClient

from backend.app import app


def test_backend_health_endpoint_works() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["api_contract"] == "v1_notation_editing_layer"


def test_backend_capabilities_expose_current_generation_contract() -> None:
    client = TestClient(app)
    response = client.get("/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_contract"] == "v1_notation_editing_layer"
    assert payload["features"]["ui_controls"] is True
    assert payload["features"]["explicit_ui_control_priority"] is True
    assert payload["features"]["backend_auto_seed"] is True
    assert payload["features"]["metadata_sync"] is True
    assert payload["features"]["editable_title_composer"] is True
    assert payload["features"]["melody_line_extraction"] is True
    assert payload["features"]["cross_measure_melodic_grammar"] is True
    assert payload["features"]["control_only_generation"] is True
    assert payload["features"]["candidate_generation"] is True
    assert payload["features"]["melody_expectation_validation"] is True
    assert payload["features"]["style_harmony_profile"] is True
    assert payload["features"]["score_document_tracks"] is True
    assert payload["features"]["phrase_level_melody"] is True
    for field in payload["required_generate_fields"]:
        assert field in payload["generate_request_fields"]


def test_openapi_generate_schema_exposes_current_fields() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    fields = set(response.json()["components"]["schemas"]["GenerateRequest"]["properties"])
    assert {
        "raw_prompt",
        "ui_controls",
        "ui_control_sources",
        "control_policy",
        "run_seed",
        "seed_source",
        "variant_id",
        "generation_nonce",
        "generation_mode",
        "candidate_count",
    }.issubset(fields)


def test_desktop_file_origin_is_allowed_by_cors() -> None:
    client = TestClient(app)
    response = client.get("/health", headers={"Origin": "null"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "null"


def test_desktop_status_publishes_serving_process_id(monkeypatch) -> None:
    monkeypatch.setenv("SERA_DESKTOP_MODE", "1")
    client = TestClient(app)

    response = client.get("/integrations/desktop/status")

    assert response.status_code == 200
    assert response.json()["desktop_available"] is True
    assert response.json()["backend_pid"] == os.getpid()
