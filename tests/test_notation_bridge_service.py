from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.integrations.notation_hosts import adapter_for, list_notation_host_capabilities
from backend.services.notation_bridge_service import NotationBridgeRevisionConflict, NotationBridgeService
from backend.services.score_document_service import musicxml_to_score_document
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.execution.transaction import PatchTransaction


ROOT = Path(__file__).resolve().parents[1]


MINIMAL_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <work><work-title>Bridge Test</work-title></work>
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
</score-partwise>
"""


def test_host_capabilities_do_not_claim_unimplemented_direct_roundtrip() -> None:
    capabilities = {item["host_id"]: item for item in list_notation_host_capabilities()}

    assert set(capabilities) == {"musicxml", "musescore", "sibelius"}
    assert capabilities["musescore"]["exchange_mode"] == "qml_saved_file_cli_bridge_versioned_musicxml"
    assert capabilities["musescore"]["bridge_status"] == "musescore_4_5_cli_fallback_ready"
    assert capabilities["musescore"]["direct_roundtrip_available"] is False
    assert capabilities["sibelius"]["direct_roundtrip_available"] is False
    assert adapter_for("musescore").revision_filename("bridge_test", 2).endswith("_r0002.musicxml")


def test_bridge_exports_versioned_revision_without_overwriting_source(tmp_path: Path) -> None:
    service = NotationBridgeService(tmp_path / "bridge")
    created = service.create_session(
        MINIMAL_MUSICXML,
        host_id="musescore",
        source_name="piece.musicxml",
        host_context={"selection": {"is_range": True, "start_measure": 1, "end_measure": 1}},
    )
    session = created["session"]
    source_path = Path(session["source_artifact"])
    original_source = source_path.read_text(encoding="utf-8")

    created["score_document"]["title"] = "Edited by Sera"
    exported = service.export_revision(
        session["session_id"],
        created["score_document"],
        expected_revision=0,
    )

    assert exported["revision"] == 1
    assert exported["export_mode"] == "source_preserving_patch"
    assert Path(exported["output_path"]).is_file()
    assert Path(exported["output_path"]) != source_path
    assert source_path.read_text(encoding="utf-8") == original_source
    assert exported["session"]["current_sha256"] != session["current_sha256"]
    workspace = service.get_workspace(session["session_id"])
    assert workspace["score_document"]["title"] == "Edited by Sera"
    assert workspace["session"]["host_context"]["selection"]["start_measure"] == 1
    assert service.get_artifact(session["session_id"], 0)["musicxml"] == MINIMAL_MUSICXML
    assert "Edited by Sera" in service.get_artifact(session["session_id"], 1)["musicxml"]

    with pytest.raises(NotationBridgeRevisionConflict):
        service.export_revision(session["session_id"], created["score_document"], expected_revision=0)


def test_bridge_exports_duration_preserving_note_to_chord_revision(tmp_path: Path) -> None:
    service = NotationBridgeService(tmp_path / "bridge")
    created = service.create_session(
        MINIMAL_MUSICXML,
        host_id="musescore",
        source_name="piece.musicxml",
    )
    score = created["score_document"]
    anchor = score["measures"][0]["events"].pop(0)
    for index, pitch in enumerate(("C4", "E4", "G4"), start=1):
        event = copy.deepcopy(anchor)
        event["event_id"] = f"bridge_chord_{index}"
        event["pitch"] = pitch
        event["is_chord_tone"] = index > 1
        event["chord_group_id"] = "bridge_chord"
        score["measures"][0]["events"].append(event)

    exported = service.export_revision(
        created["session"]["session_id"],
        score,
        expected_revision=0,
    )

    assert exported["revision"] == 1
    assert exported["export_mode"] == "source_preserving_structural_patch"
    assert exported["source_preservation"]["changed_event_count"] == 4
    assert set(exported["source_preservation"]["changed_event_ids"]) == {
        "m1_e1",
        "bridge_chord_1",
        "bridge_chord_2",
        "bridge_chord_3",
    }
    assert "<chord" in exported["musicxml"]


def test_insertion_006_gold_patch_returns_a_real_host_revision(tmp_path: Path) -> None:
    source_xml = (ROOT / "benchmark" / "source_scores" / "score_006.musicxml").read_text(encoding="utf-8")
    patch = json.loads((ROOT / "benchmark" / "gold_patches" / "insertion_006.json").read_text(encoding="utf-8"))
    service = NotationBridgeService(tmp_path / "bridge")
    created = service.create_session(source_xml, host_id="musescore", source_name="score_006.musicxml")
    before = created["score_document"]
    patch["source_score_id"] = before["score_id"]
    patch["source_fingerprint"] = score_fingerprint(before)

    applied = PatchTransaction().execute(before, patch)
    assert applied.committed is True
    exported = service.export_revision(
        created["session"]["session_id"],
        applied.score_document,
        expected_revision=0,
    )
    reparsed = musicxml_to_score_document(exported["musicxml"], source="musescore_bridge")
    replacement = [
        event
        for event in reparsed["measures"][1]["events"]
        if event.get("chord_group_id") == "insertion_006_op1"
    ]

    assert exported["revision"] == 1
    assert exported["export_mode"] == "source_preserving_structural_patch"
    assert [event["pitch"] for event in replacement] == ["C4", "E4", "G4"]
    assert all(event["duration"] == "eighth" for event in replacement)
    assert "s006_m2_rh_1" not in {
        event["event_id"]
        for event in reparsed["measures"][1]["events"]
    }
    assert [
        event["event_id"]
        for event in reparsed["measures"][2]["events"]
    ] == [
        event["event_id"]
        for event in before["measures"][2]["events"]
    ]


def test_key_001_gold_patch_returns_a_real_host_revision_without_transposition(tmp_path: Path) -> None:
    source_xml = (ROOT / "benchmark" / "source_scores" / "score_001.musicxml").read_text(encoding="utf-8")
    patch = json.loads((ROOT / "benchmark" / "gold_patches" / "key_001.json").read_text(encoding="utf-8"))
    service = NotationBridgeService(tmp_path / "bridge")
    created = service.create_session(source_xml, host_id="musescore", source_name="score_001.musicxml")
    before = created["score_document"]
    patch["source_score_id"] = before["score_id"]
    patch["source_fingerprint"] = score_fingerprint(before)
    before_pitches = {
        event["event_id"]: event.get("pitch")
        for measure in before["measures"]
        for event in measure["events"]
    }

    applied = PatchTransaction().execute(before, patch)
    assert applied.committed is True
    exported = service.export_revision(
        created["session"]["session_id"],
        applied.score_document,
        expected_revision=0,
    )
    reparsed = musicxml_to_score_document(exported["musicxml"], source="musescore_bridge")
    after_pitches = {
        event["event_id"]: event.get("pitch")
        for measure in reparsed["measures"]
        for event in measure["events"]
    }

    assert exported["revision"] == 1
    assert exported["export_mode"] == "source_preserving_global_patch"
    assert exported["source_preservation"]["changed_event_count"] == 0
    assert exported["source_preservation"]["changed_global_fields"] == ["key"]
    assert reparsed["global"]["key"] == "G major"
    assert after_pitches == before_pitches


def test_notation_bridge_api_roundtrip_and_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module = importlib.import_module("backend.app")
    monkeypatch.setattr(app_module, "notation_bridge_service", NotationBridgeService(tmp_path / "api_bridge"))
    client = TestClient(app_module.app)

    hosts = client.get("/integrations/notation-hosts")
    assert hosts.status_code == 200
    assert {item["host_id"] for item in hosts.json()["hosts"]} >= {"musescore", "sibelius"}

    created = client.post(
        "/integrations/notation-sessions",
        json={
            "host_id": "sibelius",
            "musicxml": MINIMAL_MUSICXML,
            "source_name": "source.musicxml",
            "host_context": {"selection": {"is_range": True, "start_measure": 1, "end_measure": 1}},
        },
    )
    assert created.status_code == 200
    payload = created.json()
    session_id = payload["session"]["session_id"]
    assert payload["review_path"] == f"/?bridge_session={session_id}"

    workspace = client.get(f"/integrations/notation-sessions/{session_id}/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["session"]["host_context"]["selection"]["end_measure"] == 1

    source_artifact = client.get(f"/integrations/notation-sessions/{session_id}/artifacts/0")
    assert source_artifact.status_code == 200
    assert source_artifact.headers["x-sera-bridge-revision"] == "0"
    assert "Bridge Test" in source_artifact.text

    exported = client.post(
        f"/integrations/notation-sessions/{session_id}/export",
        json={"score_document": payload["score_document"], "expected_revision": 0},
    )
    assert exported.status_code == 200
    assert exported.json()["revision"] == 1
    assert exported.json()["export_mode"] == "source_preserving_noop"

    reviewed_artifact = client.get(f"/integrations/notation-sessions/{session_id}/artifacts/1")
    assert reviewed_artifact.status_code == 200
    assert "score-partwise" in reviewed_artifact.text

    conflict = client.post(
        f"/integrations/notation-sessions/{session_id}/export",
        json={"score_document": payload["score_document"], "expected_revision": 0},
    )
    assert conflict.status_code == 409
