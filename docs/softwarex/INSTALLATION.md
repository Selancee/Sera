# Installation and reproducible environment

## Supported environment

The revision was tested on Windows 11 build 10.0.26200, Python 3.12.5,
Node.js 24.16.0 and npm 11.13.0 (3 October 2026).
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

## POSIX source-level reviewer path

The Python core is distinct from the Windows desktop/automatic host integration.
The reviewer reported that the core runs on macOS; we have not independently
retested macOS or Linux in this revision. The following are source-level commands,
not a claim that a macOS/Linux application package or automated bridge exists.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-publication.txt
python scripts/run_reviewer_demo.py
python scripts/validate_benchmark.py --split core
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Do not apply the Windows constraints as a verified POSIX lock. Save `python -m pip
freeze` and the OS/Python version when reproducing on another platform. The demo
requires no provider, host detection, Windows credential store or Node.js. Open its
exported MusicXML manually in a notation application. The HTTP schema is at
`http://127.0.0.1:8000/docs`; this route is not the automated MuseScore bridge.

For optional source UI development, use `npm --prefix frontend ci` and
`npm --prefix frontend run dev` in a second terminal. Configure optional provider
credentials through environment variables, not the Windows-only stored-credential
UI. Local-first does not mean that remote LLM mode is offline: that mode sends
instructions and score context to the chosen service.

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
.\.venv\Scripts\python.exe scripts\run_core_experiment.py --config evaluation\configs\core_mock.yaml --experiment-id reviewer_new_fixture
.\.venv\Scripts\python.exe scripts\verify_reproducibility.py --experiment softwarex_revision_verification_120_v2 --skip-tests
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

## Saved real-model evidence without new API calls

```powershell
.\.venv\Scripts\python.exe scripts/verify_reproducibility.py --experiment softwarex_deepseek_core_20261002_v1 --skip-tests --output-dir artifacts/reviewer_live_audit
```

On POSIX, replace the interpreter prefix with `python`. This verifies saved outputs;
it does not invoke DeepSeek. The exact producing implementation is fingerprinted.
Retain the immutable tested source candidate when auditing an older experiment.
See the R1 `DEEPSEEK_RESULTS.md` for results, denominators and limitations.
