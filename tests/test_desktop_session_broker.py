from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.services.desktop_session_broker import DesktopSessionBroker, desktop_session_broker
from backend.services.notation_bridge_service import NotationBridgeService


MINIMAL_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <work><work-title>Desktop Bridge Test</work-title></work>
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note></measure></part>
</score-partwise>
"""


def test_desktop_session_broker_uses_monotonic_delivery_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    broker = DesktopSessionBroker()
    monkeypatch.setenv("SERA_DESKTOP_MODE", "1")

    first = broker.publish("bridge_20260803_12345678")
    assert first["desktop_available"] is True
    assert first["pending"] is True
    assert first["delivery_mode"] == "electron_ipc"
    assert broker.snapshot(after_sequence=first["sequence"])["pending"] is False

    second = broker.publish("bridge_20260803_abcdef12")
    assert second["sequence"] == first["sequence"] + 1
    assert broker.snapshot(after_sequence=first["sequence"])["session_id"] == "bridge_20260803_abcdef12"


def test_desktop_session_broker_redelivers_after_backend_restart(monkeypatch: pytest.MonkeyPatch) -> None:
    broker = DesktopSessionBroker()
    monkeypatch.setenv("SERA_DESKTOP_MODE", "1")
    monkeypatch.setattr("backend.services.desktop_session_broker.os.getpid", lambda: 222)

    published = broker.publish("bridge_20260826_restarted")
    stale_cursor = broker.snapshot(after_sequence=99, after_backend_pid=111)

    assert published["backend_pid"] == 222
    assert stale_cursor["pending"] is True
    assert stale_cursor["session_id"] == "bridge_20260826_restarted"
    assert stale_cursor["sequence"] == 1


def test_musescore_api_publishes_session_to_desktop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_module = importlib.import_module("backend.app")
    monkeypatch.setattr(app_module, "notation_bridge_service", NotationBridgeService(tmp_path / "desktop_bridge"))
    monkeypatch.setenv("SERA_DESKTOP_MODE", "1")
    desktop_session_broker.reset()


def test_existing_notation_session_can_be_reactivated_without_creating_a_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_module = importlib.import_module("backend.app")
    monkeypatch.setattr(app_module, "notation_bridge_service", NotationBridgeService(tmp_path / "desktop_bridge"))
    monkeypatch.setenv("SERA_DESKTOP_MODE", "1")
    desktop_session_broker.reset()
    client = TestClient(app_module.app)

    created = client.post(
        "/integrations/notation-sessions",
        json={
            "host_id": "musescore",
            "musicxml": MINIMAL_MUSICXML,
            "source_name": "desktop.musicxml",
            "host_context": {
                "bridge": "sera_musescore_qml",
                "selection": {"is_range": True, "start_measure": 1, "end_measure": 1},
            },
        },
    ).json()
    session_id = created["session"]["session_id"]
    first_sequence = created["desktop_delivery"]["sequence"]

    activated = client.post(f"/integrations/notation-sessions/{session_id}/activate")

    assert activated.status_code == 200
    payload = activated.json()
    assert payload["session"]["session_id"] == session_id
    assert payload["session"]["revision"] == 0
    assert payload["desktop_delivery"]["session_id"] == session_id
    assert payload["desktop_delivery"]["sequence"] == first_sequence + 1
    assert len(list((tmp_path / "desktop_bridge" / session_id).glob("*_r*.musicxml"))) == 0
    desktop_session_broker.reset()
    client = TestClient(app_module.app)

    created = client.post(
        "/integrations/notation-sessions",
        json={
            "host_id": "musescore",
            "musicxml": MINIMAL_MUSICXML,
            "source_name": "desktop.musicxml",
            "host_context": {
                "bridge": "sera_musescore_qml",
                "selection": {"is_range": True, "start_measure": 1, "end_measure": 1},
            },
        },
    )

    assert created.status_code == 200
    delivery = created.json()["desktop_delivery"]
    assert delivery["desktop_available"] is True
    assert delivery["pending"] is True

    pending = client.get("/integrations/desktop/pending-session?after_sequence=0")
    assert pending.status_code == 200
    assert pending.json()["session_id"] == created.json()["session"]["session_id"]

    consumed = client.get(
        f"/integrations/desktop/pending-session?after_sequence={delivery['sequence']}"
    )
    assert consumed.status_code == 200
    assert consumed.json()["pending"] is False
    desktop_session_broker.reset()
