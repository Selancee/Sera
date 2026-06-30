from fastapi.testclient import TestClient

from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.app import app
from backend.generation.rule_based_generator import RuleBasedGenerator
from backend.models.schemas import StructuredMusicIntent


def test_workbench_import_operation_patch_and_export_api() -> None:
    client = TestClient(app)
    plan = CompositionPlanningAgent().plan(StructuredMusicIntent(prompt="8 bar C major piano", bars=8))
    generated = RuleBasedGenerator().generate(plan)

    imported = client.post("/score/import_musicxml", json={"musicxml": generated.musicxml}).json()
    score_document = imported["score_document"]
    operation_payload = client.post(
        "/score/apply_operation",
        json={
            "score_document": score_document,
            "operation": {
                "source": "user",
                "type": "insert_note",
                "target": {"measure": 1},
                "after": {"pitch": "C4", "duration": "quarter", "offset": 0},
                "description": "Insert C4",
            },
            "operation_history": imported["operation_history"],
        },
    )
    assert operation_payload.status_code == 200
    edited = operation_payload.json()["score_document"]

    patch_preview = client.post(
        "/score/agent_edit",
        json={
            "score_document": edited,
            "instruction": "add cadence to the ending",
            "selected_range": {"start_measure": 7, "end_measure": 8},
            "constraints": {"preserve_form": True},
        },
    )
    assert patch_preview.status_code == 200
    export_payload = client.post("/score/export_musicxml", json={"score_document": edited})
    assert export_payload.status_code == 200
    assert "score-partwise" in export_payload.json()["musicxml"]


def test_workbench_v07_patch_validation_partial_apply_and_explain_api() -> None:
    client = TestClient(app)
    plan = CompositionPlanningAgent().plan(StructuredMusicIntent(prompt="8 bar C major piano", bars=8))
    generated = RuleBasedGenerator().generate(plan)
    score_document = client.post("/score/import_musicxml", json={"musicxml": generated.musicxml}).json()["score_document"]

    preview = client.post(
        "/score/agent_edit",
        json={
            "score_document": score_document,
            "instruction": "make the ending more conclusive",
            "selected_range": {"start_measure": 7, "end_measure": 8},
            "constraints": {"preserve_form": True, "patch_size_limit": "small"},
        },
    )
    assert preview.status_code == 200
    patch = preview.json()["patch"]

    validation = client.post(
        "/score/validate_patch",
        json={
            "score_document": score_document,
            "patch": patch,
            "instruction": "make the ending more conclusive",
            "selected_range": {"start_measure": 7, "end_measure": 8},
            "constraints": {"preserve_form": True},
        },
    )
    assert validation.status_code == 200
    assert validation.json()["patch_validation_report"]["target_range_valid"] is True

    partial = client.post(
        "/score/partial_apply_patch",
        json={
            "score_document": score_document,
            "patch": patch,
            "instruction": "make the ending more conclusive",
            "selected_range": {"start_measure": 7, "end_measure": 8},
            "constraints": {"preserve_form": True},
            "operation_indexes": [0],
        },
    )
    assert partial.status_code == 200
    assert partial.json()["partial"] is True

    explanation = client.post(
        "/score/explain_selection",
        json={
            "score_document": score_document,
            "selected_range": {"start_measure": 1, "end_measure": 2},
            "question": "explain this passage",
        },
    )
    assert explanation.status_code == 200
    assert explanation.json()["explanation"]["summary"]

    capabilities = client.get("/score/render_capabilities")
    health = client.get("/score/workbench_health")
    assert capabilities.status_code == 200
    assert "fallback" in capabilities.json()["renderer_modes"]
    assert health.json()["mock_fallback"] is True
