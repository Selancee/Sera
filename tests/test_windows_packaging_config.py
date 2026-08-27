import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_electron_builder_config_packages_backend_and_frontend() -> None:
    package = json.loads((ROOT / "electron" / "package.json").read_text(encoding="utf-8"))
    build = package["build"]

    assert "electron-builder" in package["devDependencies"]
    assert package["scripts"]["dist"] == "electron-builder --win dir --x64"
    assert package["scripts"]["dist:portable"] == "electron-builder --win portable --x64"
    assert build["directories"]["output"] == "../dist_desktop/release"
    assert {"target": "dir", "arch": ["x64"]} in build["win"]["target"]
    assert {"target": "portable", "arch": ["x64"]} in build["win"]["target"]

    resources = {(item["from"], item["to"]) for item in build["extraResources"]}
    assert ("../dist_desktop/backend", "backend") in resources
    assert ("../dist_desktop/frontend", "frontend") in resources


def test_windows_scripts_build_and_smoke_desktop_exe() -> None:
    build_script = (ROOT / "packaging" / "windows" / "build_windows_app.ps1").read_text(encoding="utf-8")
    smoke_script = (ROOT / "packaging" / "windows" / "smoke_test_packaged_app.ps1").read_text(encoding="utf-8")

    assert "npm.cmd run dist" in build_script
    assert "--ignore-scripts" in build_script
    assert "ELECTRON_BUILDER_CACHE" in build_script
    assert "release_manifest.json" in build_script
    assert "packaging\\desktop\\build_desktop_exe.py" in build_script
    assert "runtime_desktop_launcher" in smoke_script
    assert "Desktop launcher exe smoke passed" in smoke_script
    assert "sera-desktop-shell\\runtime" in smoke_script
    assert "ElectronBackendExe" in smoke_script
    assert "CloseMainWindow" in smoke_script
    assert "Electron backend process tree was not released" in smoke_script


def test_pyinstaller_entrypoints_use_onedir_without_temp_extraction() -> None:
    backend_spec = (ROOT / "packaging" / "backend" / "backend.spec").read_text(encoding="utf-8")
    desktop_spec = (ROOT / "packaging" / "desktop" / "desktop.spec").read_text(encoding="utf-8")
    build_script = (ROOT / "packaging" / "windows" / "build_windows_app.ps1").read_text(encoding="utf-8")

    for spec in (backend_spec, desktop_spec):
        assert "exclude_binaries=True" in spec
        assert "COLLECT(" in spec
        assert "runtime_tmpdir" not in spec

    assert "$Root\\dist\\SeraBackend\\SeraBackend.exe" in build_script
    assert "$Root\\dist\\Sera\\Sera.exe" in build_script
    assert 'Copy-Item -Recurse -Force "$Root\\dist\\SeraBackend\\*" $BackendOut' in build_script
    assert 'Copy-Item -Recurse -Force "$Root\\dist\\Sera\\*" $DesktopRoot' in build_script
