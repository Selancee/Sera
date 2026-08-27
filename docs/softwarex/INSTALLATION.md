# Installation and reproducible environment

## Supported environment

The research source is tested on 64-bit Windows 11 with Python 3.12 and Node.js.
The Python package declares Python 3.10 or newer. The Electron desktop package is
currently Windows-only. MuseScore Studio 4.x is optional and is required only for
the notation-host bridge; the benchmark and core transaction tests run without it.

## Minimum reviewer installation

From PowerShell in the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-publication.txt -c requirements-tested-windows.txt
.\.venv\Scripts\python.exe scripts\run_reviewer_demo.py
```

The last command is an offline, six-task end-to-end demonstration and should report
`6/6 passed` with five host-openable MusicXML revisions. It requires neither Node.js,
MuseScore, an API key, nor a network connection. See `docs/softwarex/REVIEWER_GUIDE.md`
for the evidence map.

`requirements-tested-windows.txt` pins the direct dependency versions used for the
2026-08-27 verification. It is intentionally a constraints file: pip still resolves
transitive packages, while experiment manifests preserve a dependency inventory and
hash for drift checking.

## Optional frontend and desktop development

The reviewer demo and research runners do not require this section. To modify the
React/Electron interface, install Node.js and run:

```powershell

Set-Location frontend
npm.cmd ci
npm.cmd run build
Set-Location ..

Set-Location electron
npm.cmd ci
Set-Location ..
```

`npm ci` uses committed lock files. MuseScore Studio 4.x is required only for visual
host inspection and the optional bridge workflow.

## Run the development application

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

In a second PowerShell window:

```powershell
Set-Location frontend
npm.cmd run dev
```

The API schema is available locally at `http://127.0.0.1:8000/docs`. API keys are
optional and must remain in the user-local settings store or environment variables.
The deterministic mock path and benchmark do not require a network connection.

## Run the packaged Windows application

The current locally verified executable is:

```text
dist_desktop\release\win-unpacked\Sera.exe
```

This build directory is not the archival source distribution. Rebuild and verify it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\windows\build_windows_app.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\windows\smoke_test_packaged_app.ps1
```

## Reproduce the software verification

```powershell
.\.venv\Scripts\python.exe scripts\run_reviewer_demo.py
.\.venv\Scripts\python.exe scripts\validate_benchmark.py --split core --write-report
.\.venv\Scripts\python.exe scripts\run_core_experiment.py --config evaluation\configs\core_mock.yaml --experiment-id softwarex_verification_120_v1
.\.venv\Scripts\python.exe scripts\verify_reproducibility.py --experiment softwarex_verification_120_v1 --skip-tests
.\.venv\Scripts\python.exe scripts\verify_softwarex_package.py --profile draft
```

The `core_mock.yaml` result is a deterministic pipeline fixture. It tests parsing,
validation, transaction, round-trip and metric plumbing; it is not an LLM benchmark.

## Complete regression commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend test -- --run
npm.cmd --prefix frontend run build
```

The intentional error messages printed by `RuntimeErrorBoundary.test.jsx` exercise
the UI error boundary; the Vitest exit code and final summary determine success.
