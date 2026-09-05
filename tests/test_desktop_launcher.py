import importlib.util
import json
import socket
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]


def load_desktop_launcher_module():
    path = ROOT / "packaging" / "desktop" / "run_desktop_app.py"
    spec = importlib.util.spec_from_file_location("sera_desktop_launcher", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_desktop_launcher_port_file_and_port_selection(tmp_path) -> None:
    module = load_desktop_launcher_module()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        occupied = busy.getsockname()[1]

        selected = module.find_available_port(occupied, max_attempts=3)

    assert selected != occupied
    path = module.write_runtime_port_file(8124, tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["base_url"] == "http://127.0.0.1:8124"


def test_desktop_launcher_serves_frontend_index(tmp_path) -> None:
    module = load_desktop_launcher_module()
    frontend = tmp_path / "frontend_dist"
    assets = frontend / "assets"
    assets.mkdir(parents=True)
    (frontend / "index.html").write_text("<html>Sera Desktop</html>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('sera')", encoding="utf-8")

    app = FastAPI()
    module.configure_frontend_routes(app, frontend)
    client = TestClient(app)

    assert "Sera Desktop" in client.get("/").text
    assert "Sera Desktop" in client.get("/workbench").text
    assert client.get("/assets/app.js").text == "console.log('sera')"


def test_desktop_launcher_disables_uvicorn_console_log_config() -> None:
    source = (ROOT / "packaging" / "desktop" / "run_desktop_app.py").read_text(encoding="utf-8")
    assert "log_config=None" in source
    assert 'SERA_ALLOW_EXTERNAL_BROWSER", "").strip() != "1"' in source


def test_electron_shell_receives_musescore_sessions_without_external_browser() -> None:
    main = (ROOT / "electron" / "main.js").read_text(encoding="utf-8")
    preload = (ROOT / "electron" / "preload.js").read_text(encoding="utf-8")
    qml = (ROOT / "integrations" / "musescore" / "SeraBridge" / "SeraBridge.qml").read_text(encoding="utf-8")

    assert "/integrations/desktop/pending-session" in main
    assert "after_backend_pid" in main
    assert "backendChanged" in main
    assert "latestDesktopSession.backend_pid !== backendPid" in main
    assert 'win.webContents.send("sera:open-session"' in main
    assert "bringWindowToFront(win)" in main
    assert "app.focus()" in main
    assert 'win.setAlwaysOnTop(true, "screen-saver")' in main
    assert "win.setAlwaysOnTop(false)" in main
    assert 'ipcRenderer.on("sera:open-session"' in preload
    assert "readPendingSession" in preload
    assert "Qt.openUrlExternally" not in qml


def test_electron_shell_adopts_and_terminates_packaged_backend_process_tree() -> None:
    main = (ROOT / "electron" / "main.js").read_text(encoding="utf-8")

    assert "probeExistingDesktopBackend" in main
    assert "/integrations/desktop/status" in main
    assert "status.desktop_available !== true" in main
    assert "status.backend_pid" in main
    assert '"System32", "taskkill.exe"' in main
    assert "result.status === 0" in main
    assert '["/pid", String(processId), "/T", "/F"]' in main
    assert 'app.on("before-quit", stopBackend)' in main


def test_electron_shell_waits_for_backend_health_and_shows_inline_startup_state() -> None:
    main = (ROOT / "electron" / "main.js").read_text(encoding="utf-8")

    assert "waitForBackendReady" in main
    assert 'return app.isPackaged ? 90000 : 45000' in main
    assert '`${runtime.base_url.replace(/\\/$/, "")}/health`' in main
    assert "Starting the Sera local engine" in main
    assert "First startup usually takes 15–60 seconds" in main
    assert '<html lang="en">' in main
    assert "show: false" in main
    assert "await showStartupPage(win)" in main
    assert "win.show()" in main
    assert "dialog.showErrorBox" not in main
    assert main.index("await ensureBackend()") < main.index("await win.loadFile(indexPath")


def test_frontend_build_uses_relative_assets_for_file_protocol() -> None:
    vite_config = (ROOT / "frontend" / "vite.config.js").read_text(encoding="utf-8")

    assert 'base: "./"' in vite_config


def test_start_script_checks_backend_api_contract() -> None:
    source = (ROOT / "scripts" / "start_sera.ps1").read_text(encoding="utf-8")

    assert "/capabilities" in source
    assert "v1_notation_editing_layer" in source
    for field in ("raw_prompt", "ui_controls", "ui_control_sources", "control_policy", "run_seed", "candidate_generation", "style_harmony_profile", "phrase_level_melody"):
        assert field in source


def test_default_launcher_uses_electron_desktop_and_preserves_web_compatibility() -> None:
    default_launcher = (ROOT / "run_app.bat").read_text(encoding="utf-8")
    web_launcher = (ROOT / "run_web_app.bat").read_text(encoding="utf-8")
    desktop_script = (ROOT / "scripts" / "start_sera_desktop.ps1").read_text(encoding="utf-8")

    assert "start_sera_desktop.ps1" in default_launcher
    assert "dist_desktop\\release\\win-unpacked\\Sera.exe" in default_launcher
    assert "release-dev" not in default_launcher
    assert "start_sera.ps1" in web_launcher
    assert "No external browser will be opened" in desktop_script
    assert "SERA_DESKTOP_MODE" in desktop_script
