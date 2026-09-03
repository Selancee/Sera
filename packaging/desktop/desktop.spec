# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path.cwd()
frontend_dist = project_root / "frontend" / "dist"

a = Analysis(
    [str(project_root / "packaging" / "desktop" / "run_desktop_app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "backend"), "backend"),
        (str(project_root / "benchmark"), "benchmark"),
        (str(project_root / "evaluation"), "evaluation"),
        (
            str(project_root / "experiments" / "softwarex_runtime_acceptance_720_v4"),
            "experiments/softwarex_runtime_acceptance_720_v4",
        ),
        (
            str(project_root / "experiments" / "softwarex_host_scope_robustness_240_v3"),
            "experiments/softwarex_host_scope_robustness_240_v3",
        ),
        (str(project_root / "sera_edit" / "composer" / "style_kb"), "sera_edit/composer/style_kb"),
        (str(frontend_dist), "frontend_dist"),
        (str(project_root / ".env.example"), "."),
    ],
    hiddenimports=["uvicorn", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Sera",
    icon=str(project_root / "assets" / "branding" / "sera-icon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Sera",
)
