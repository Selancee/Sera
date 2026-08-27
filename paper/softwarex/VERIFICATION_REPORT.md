# SoftwareX verification report

- Verification date: 2026-08-27
- Software version: `1.0.0`
- Baseline Git commit recorded by experiments: `b4eb13921bcbc48a95136cc744cabc094112a541`
- Release commit and clean-worktree state: recorded by `release/release_manifest.json`

## Environment

- Microsoft Windows 11 Home (Chinese), build `10.0.26200`;
- Python `3.12.5` in `D:\Sera\.venv`;
- Node.js `24.16.0`;
- npm `11.13.0`;
- Electron package version `1.0.0`.

## Executed checks

| Check | Command/evidence | Result |
| --- | --- | --- |
| Benchmark schema, gold and MusicXML round trip | `scripts/validate_benchmark.py --split core --write-report` | 120 valid, 0 invalid |
| Human task/Gold review | `experiments/softwarex_human_review_120_v1` | 120/120 primary, 30/30 stratified repeat, 0 stale; same reviewer, no inter-rater claim |
| Offline three-condition runner | `scripts/run_core_experiment.py ... softwarex_verification_120_v1` | 360/360 complete; 0 errors; non-formal mock fixture |
| Product runtime replay | `scripts/run_runtime_acceptance.py --split core --languages en zh --repetitions 3 --mode local` | 720/720 passed; 660/660 executable runs completed source-preserving host export/re-import; 60 correct refusals; 0 unsafe executions; complete preservation 1.0 |
| Host-selection localization replay | `scripts/run_runtime_acceptance.py ... --host-scope-mode expanded_adjacent` | 240/240 passed; 220/220 executable runs completed source-preserving host export/re-import; 174/174 widened-selection runs passed; 0 unsafe executions |
| Experiment drift/recompute | `scripts/verify_reproducibility.py --experiment softwarex_verification_120_v1 --skip-tests` | All 7 evidence checks true |
| Human-review evidence/API | frozen API export plus `tests/test_human_review_evidence_export.py` | 120/120 primary, 30/30 repeated checks, 194 audit records; frozen hashes match |
| Python regression | `.venv\Scripts\python.exe -m pytest -q` | 408 collected and passed |
| Frontend regression | `npm.cmd test -- --run` | 72 files, 120 tests passed |
| Frontend production build | `npm.cmd run build` | 216 modules transformed; build passed |
| Offline reviewer demo | `scripts/run_reviewer_demo.py` | 6/6 representative tasks passed; 5/5 executable tasks produced host-openable MusicXML |
| Windows research CI | `.github/workflows/research-ci.yml` | Workflow prepared; local equivalents passed before push |
| Rendered review workflow | Agent -> Research review -> save -> progress/next task | Passed against real local API; no console warnings/errors |
| Ordinary packaged runtime | `dist_desktop/release/win-unpacked/Sera.exe` | Review entry hidden by default; backend readiness, launcher and Electron startup passed |
| Windows package smoke | `smoke_test_packaged_app.ps1` | Frozen 120-task evidence, exact `compound_001` scope, `meter_001`, `voice_010`/`voice_004` source-preserving revisions and launcher/Electron runtime passed |
| Architecture figure | Mermaid CLI validation and SVG/PNG/PDF export; PNG visually inspected | Passed after one layout refinement |
| DOCX structure | `python-docx` inspection | 3 tables, 1 embedded figure, line numbers, title present |
| PDF compilation and visual QA | bundled Tectonic 0.17.0 plus 8 rendered-page inspection | 8 pages, all pages readable, figure/table visible, no replacement characters; only minor box-spacing warnings |
| Draft package verifier | `verify_softwarex_package.py --profile draft` | Passed; strict profile has only seven author-controlled blockers |
| Release archive integrity | `ZipFile.testzip()` plus allowlist inspection | Source/reviewer ZIP CRC passed; frozen human summary/manifest present; no `.env` or `node_modules` |

The repeated `generated result render failed` messages printed during Vitest are the
deliberate input of `RuntimeErrorBoundary.test.jsx`; the suite exit code was zero and
all 120 tests passed.

## Experiment interpretation

`softwarex_verification_120_v1` uses `mock:benchmark-fixture-v2-roundtrip`, temperature
0 and seed 42. It verifies parsing, condition routing, patch application, validation,
round trips, output storage and deterministic metric recomputation. The manifest has
`formal_results_allowed: false`; its success/minimality/preservation values must not be
reported as language-model accuracy. No provider key or private score is included.

`runtime_acceptance_core_bilingual_r3_v4_20260826` is a separate deterministic
product-path replay, not one of the formal model conditions. It retains 720 raw outputs,
660 host outputs created by patching the original MusicXML source, hashes for all 1,380
evidence files, and 220 compact outputs for complete desktop review. Its manifest explicitly
disallows use as remote-model or aesthetic evidence.
All 120 task groups produced equivalent patch semantics and identical final score
fingerprints across English and Chinese instructions.

`runtime_acceptance_host_roundtrip_scope_v2_20260826` is a second product-path replay.
It widened eligible explicit-measure host selections by one adjacent measure while
leaving each instruction unchanged. All 240 bilingual runs passed; expansion applied
to 174 runs and all 174 preserved the benchmark target, protected content and valid
MusicXML. All 220 executable runs completed source-preserving host export/re-import; its
publication snapshot hashes 460 raw/host files. The frozen-package smoke
also replayed `compound_001` with host measures 2-3 and verified that only
`s007_m2_rh_3` and `s007_m2_rh_4` changed.

## Manuscript checks

- Numbered Sections 1-5: 1747 words by the repository verifier;
- Abstract: 105 words;
- Keywords: 6;
- Numbered manuscript figures: 1;
- Code metadata C1-C9 and executable metadata S1-S8: included;
- Official v4 structural basis: `elsarticle`, preprint single column, line numbers,
  numbered Sections 1-5, metadata tables and numeric references.

The LaTeX source compiled successfully with bundled Tectonic 0.17.0 to an eight-page
review PDF. All eight pages were rasterized and visually inspected: text, metadata
tables, architecture figure, evidence table, line numbers and references are present
and readable. Extracted text contains no Unicode replacement characters. The remaining
TeX messages are minor underfull/overfull box-spacing warnings rather than compilation
errors. The line-numbered DOCX was regenerated and structurally validated as an
alternative review format.

## Release hashes

- Windows x64 portable: `66052a05c9f526b0dc44d125d0bc1449998cc8db7b3b53876c7cb0a5b9b7b756`;
- source ZIP: `7ae6a9ab20c29279fb04872fee8fa549d4f6a361dba571821c38c608c4b4e0e6`;
- manuscript/reviewer ZIP: `f3cdf06e2210aa7d9e37511067f5e7bed4e7cdea5b5b236457ba412b578d3444`;
- immutable tag commit: `b23afcf08c26c46625fc3f24d82882495de9348f`.

The public release is `https://github.com/Selancee/Sera/releases/tag/v1.0.0`.
Anonymous GitHub API verification confirmed that it is published, not a draft or
prerelease, and that all five uploaded asset digests match the local SHA-256 values.

## Submission blockers

- DOI `10.5281/zenodo.22128976` is reserved and inserted in C3/S3, but Zenodo draft
  record `22128976` is not yet publicly published.

This is deliberately detected by the strict verifier. It is not a software-test failure:
the archive gate clears only after the corresponding author publishes the Zenodo record.
