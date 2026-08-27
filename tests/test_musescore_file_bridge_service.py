from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.services.desktop_session_broker import desktop_session_broker
from backend.services.musescore_file_bridge_service import MuseScoreFileBridgeError, MuseScoreFileBridgeService
from backend.services.notation_bridge_service import NotationBridgeService


MINIMAL_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <work><work-title>MuseScore CLI Bridge Test</work-title></work>
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note></measure></part>
</score-partwise>
"""


def test_reads_direct_musicxml_from_file_url_without_musescore_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    source.write_text(MINIMAL_MUSICXML, encoding="utf-8")
    service = MuseScoreFileBridgeService(tmp_path, executable_resolver=lambda: "")

    result = service.import_saved_score(source.as_uri())

    assert result["conversion_mode"] == "direct_musicxml"
    assert result["source_path"] == str(source.resolve())
    assert "MuseScore CLI Bridge Test" in result["musicxml"]


def test_converts_saved_mscz_with_musescore_cli_contract(tmp_path: Path) -> None:
    executable = tmp_path / "MuseScore4.exe"
    executable.write_bytes(b"fake")
    source = tmp_path / "source.mscz"
    source.write_bytes(b"saved score")
    commands: list[list[str]] = []

    def fake_runner(command: list[str], **_: object) -> SimpleNamespace:
        commands.append(command)
        output = Path(command[3])
        output.write_text(MINIMAL_MUSICXML, encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    service = MuseScoreFileBridgeService(
        tmp_path,
        executable_resolver=lambda: str(executable),
        runner=fake_runner,
    )

    result = service.import_saved_score(str(source))

    assert result["conversion_mode"] == "musescore_cli"
    assert commands == [[str(executable.resolve()), str(source.resolve()), "-o", commands[0][3]]]
    assert commands[0][3].endswith("source.musicxml")


def test_rejects_missing_or_unsupported_source_files(tmp_path: Path) -> None:
    service = MuseScoreFileBridgeService(tmp_path, executable_resolver=lambda: "")

    with pytest.raises(MuseScoreFileBridgeError, match="does not exist"):
        service.import_saved_score(str(tmp_path / "missing.mscz"))

    unsupported = tmp_path / "source.pdf"
    unsupported.write_bytes(b"pdf")
    with pytest.raises(MuseScoreFileBridgeError, match="Unsupported"):
        service.import_saved_score(str(unsupported))


def test_file_bridge_api_creates_session_and_opens_reviewed_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_module = importlib.import_module("backend.app")
    monkeypatch.setattr(app_module, "notation_bridge_service", NotationBridgeService(tmp_path / "sessions"))
    monkeypatch.setenv("SERA_DESKTOP_MODE", "1")
    desktop_session_broker.reset()
    opened_paths: list[str] = []

    class FakeMuseScoreBridge:
        def import_saved_score(self, source_path: str) -> dict[str, object]:
            return {
                "musicxml": MINIMAL_MUSICXML,
                "source_path": source_path,
                "source_name": "source.mscz",
                "source_suffix": ".mscz",
                "conversion_mode": "musescore_cli",
                "musescore_executable": "MuseScore4.exe",
                "latency_ms": 1.0,
            }

        def open_reviewed_score(self, score_path: str) -> dict[str, object]:
            opened_paths.append(score_path)
            return {
                "opened": True,
                "process_id": 42,
                "musescore_executable": "MuseScore4.exe",
                "score_path": score_path,
                "delivery_mode": "musescore_cli_open_new_tab",
            }

    monkeypatch.setattr(app_module, "musescore_file_bridge_service", FakeMuseScoreBridge())
    client = TestClient(app_module.app)

    created = client.post(
        "/integrations/musescore-file-sessions",
        json={
            "source_path": "D:/scores/source.mscz",
            "host_context": {
                "bridge": "sera_musescore_qml_cli",
                "selection": {"is_range": True, "start_measure": 1, "end_measure": 1},
            },
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["source_conversion"]["conversion_mode"] == "musescore_cli"
    assert payload["desktop_delivery"]["pending"] is True
    session_id = payload["session"]["session_id"]

    exported = client.post(
        f"/integrations/notation-sessions/{session_id}/export",
        json={"score_document": payload["score_document"], "expected_revision": 0},
    )
    assert exported.status_code == 200

    opened = client.post(
        f"/integrations/notation-sessions/{session_id}/open-in-musescore",
        json={"revision": 1},
    )
    assert opened.status_code == 200
    assert opened.json()["opened"] is True
    assert opened_paths and opened_paths[0].endswith(".musicxml")
    desktop_session_broker.reset()
