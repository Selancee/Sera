# Sera Windows Executable Packaging

Sera keeps the normal developer workflow unchanged:

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
cd frontend
npm run dev
```

The desktop route builds and packages:

- React/Vite frontend build under `dist_desktop/frontend/dist`
- PyInstaller onedir backend under `dist_desktop/backend` with its executable at `SeraBackend.exe`
- Legacy PyInstaller onedir compatibility launcher under `dist_desktop` with its executable at `Sera.exe`
- Electron shell files under `dist_desktop/electron`
- Required Electron unpacked desktop exe under `dist_desktop/release/win-unpacked/Sera.exe`
- Required Electron portable desktop exe under `dist_desktop/release/Sera-<version>-x64.exe`
- Release manifest under `dist_desktop/release_manifest.json`

Recommended baseline before packaging:

```powershell
cd D:\Sera
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm.cmd run build
npm.cmd test
cd ..
.\.venv\Scripts\python.exe -m evaluation.v093_real_score_and_notation.run_v093_eval --max-prompts 3
```

Build:

```powershell
cd D:\Sera
packaging\windows\build_windows_app.bat
```

Smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\smoke_test_packaged_app.ps1
```

Backend startup:

- The backend defaults to port `8000`; Electron desktop mode reserves that fixed port for notation-host plug-ins and fails clearly if another application owns it.
- The standalone legacy launcher may select the next available local port.
- The selected port is written to `backend_port.json` in the runtime directory.
- `dist_desktop/Sera.exe` serves the bundled frontend and backend from one local FastAPI process and writes the runtime port file, but does not open a browser by default and is not the primary desktop UI.
- The Electron main process deletes stale port metadata, starts `SeraBackend.exe`, waits for a fresh port file, and then loads the frontend bundle.
- Both frozen Python entrypoints use PyInstaller onedir distributions. They run in place and do not extract `_MEI*` payloads into `%TEMP%` on each launch.
- No real API key is bundled; `.env` stays external.

Troubleshooting:

- If the UI opens but the backend is unavailable, check the runtime `backend_port.json` and backend logs.
- If PyInstaller is missing, install it into the project virtual environment.
- If Electron packaging dependencies are missing, run `npm.cmd install --no-audit --no-fund` under `D:\Sera\electron`.
- If Electron runtime download fails, retry `npm.cmd install --no-audit --no-fund`; a no-browser release is incomplete until the Electron artifacts exist.
- If port `8000` is busy, the runtime file shows the actual selected port.
- If a previous packaged app locks output files, close Sera or let `build_windows_app.ps1` stop `Sera.exe` and `SeraBackend.exe` processes launched from this checkout.
