from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QML_PATH = PROJECT_ROOT / "integrations" / "musescore" / "SeraBridge" / "SeraBridge.qml"
INSTALLER_PATH = PROJECT_ROOT / "scripts" / "install_musescore_bridge.ps1"


def test_musescore_bridge_uses_saved_file_cli_fallback_for_musescore_4_5() -> None:
    qml = QML_PATH.read_text(encoding="utf-8")

    assert "import MuseScore 3.0" in qml
    assert "writeScore(" not in qml
    assert "readScore(" not in qml
    assert "FileDialog" in qml
    assert "scoreFileDialog.filePath" in qml
    assert "selection.startSegment.tick" in qml
    assert "selection.endSegment.tick" in qml
    assert 'request("POST", "/integrations/musescore-file-sessions"' in qml
    assert '"/open-in-musescore"' in qml
    assert '"/activate"' in qml
    assert "Sera Desktop was focused on this exact session" in qml
    assert "Refresh and open applied revision" in qml


def test_musescore_bridge_is_non_destructive_and_has_no_embedded_secret() -> None:
    qml = QML_PATH.read_text(encoding="utf-8")

    assert 'version: "0.3.3"' in qml
    assert "The original source window is intentionally unchanged" in qml
    assert "already open in a separate MuseScore window" in qml
    assert "No response from Sera" in qml
    assert "curScore.startCmd" not in qml
    assert "curScore.endCmd" not in qml
    assert "api_key" not in qml.lower()
    assert "bearer " not in qml.lower()
    assert "Qt.openUrlExternally" not in qml
    assert "frontendBaseUrl" not in qml
    assert "desktop_delivery" in qml


def test_musescore_installer_refuses_to_overwrite_existing_plugin() -> None:
    installer = INSTALLER_PATH.read_text(encoding="utf-8")

    assert "SpecialFolder]::MyDocuments" in installer
    assert 'Join-Path $documents "MuseScore4\\Plugins"' in installer
    assert "Refusing to overwrite an existing MuseScore plugin folder" in installer
    assert "UpdateExisting" in installer
    assert "SeraBridge.backup_" in installer
