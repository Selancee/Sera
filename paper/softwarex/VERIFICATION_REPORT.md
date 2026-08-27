# SoftwareX verification report

Verification date: 2026-08-27  
Software version: `1.0.0-dev.14`  
Baseline Git commit recorded by experiments: `b4eb13921bcbc48a95136cc744cabc094112a541`  
Worktree: dirty; release archives therefore use an explicit file/hash manifest.

## Environment

- Microsoft Windows 11 Home (Chinese), build `10.0.26200`;
- Python `3.12.5` in `D:\Sera\.venv`;
- Node.js `24.16.0`;
- npm `11.13.0`;
- Electron package version `1.0.0-dev.14`.

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
| Python regression | `.venv\Scripts\python.exe -m pytest -q` | 404 collected and passed |
| Frontend regression | `npm.cmd test -- --run` | 72 files, 120 tests passed |
| Frontend production build | `npm.cmd run build` | 216 modules transformed; build passed |
| Rendered review workflow | Agent -> Research review -> save -> progress/next task | Passed against real local API; no console warnings/errors |
| Ordinary packaged runtime | `dist_desktop/release/win-unpacked/Sera.exe` | Review entry hidden by default; backend readiness, launcher and Electron startup passed |
| Windows package smoke | `smoke_test_packaged_app.ps1` | Frozen 120-task evidence, exact `compound_001` scope, `meter_001`, `voice_010`/`voice_004` source-preserving revisions and launcher/Electron runtime passed |
| Architecture figure | Mermaid CLI validation and SVG/PNG/PDF export; PNG visually inspected | Passed after one layout refinement |
| DOCX structure | ZIP/XML inspection | 2 metadata tables, 1 embedded figure, line numbers, title present |
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

- Numbered Sections 1-5: 1675 words by the repository verifier;
- Abstract: 105 words;
- Keywords: 6;
- Numbered manuscript figures: 1;
- Code metadata C1-C9 and executable metadata S1-S8: included;
- Official v4 structural basis: `elsarticle`, preprint single column, line numbers,
  numbered Sections 1-5, metadata tables and numeric references.

The LaTeX source was inspected by the compile helper, but a final PDF was not produced:
no TeX Live installation exists and the bundled Tectonic package fetch failed while
retrieving a hyphenation resource because the TLS connection ended early. The line-numbered DOCX
was generated and structurally validated. A final submission PDF should be compiled on
Overleaf/TeX Live, or the user may explicitly authorize the large managed TeX Live
installation.

## Release hashes

- unpacked desktop: `fd09c1e98dbeafa5362d3534dee2ecbcd45ac2da7193804ec3c75f8de9ec087a`;
- packaged backend: `d682393db5a8fa7bb5bbcf92f93f0780adf6dbe1bc6703bbbcbd86efb71304e9`;
- source and manuscript/reviewer ZIP: see the external deterministic release manifest.

## Submission blockers

- configured GitHub repository is not publicly readable without authentication;
- no immutable release tag or permanent archive DOI;
- copyright owner has not confirmed the MIT public release;
- author name, affiliation and support email remain placeholders;
- funding, competing-interest and CRediT text require author confirmation.

These are deliberately detected by the strict verifier. They are not software-test
failures and cannot be completed truthfully without the author's information/authority.
