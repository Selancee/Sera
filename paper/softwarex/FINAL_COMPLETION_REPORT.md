# SoftwareX preparation completion report

## Delivered

The repository now contains an independent SoftwareX release track for SeraEdit
`1.0.0`: open-source/citation metadata, rights inventory, research-software
documentation, a v4-structured OSP manuscript in Markdown/LaTeX/DOCX, architecture
figure sources and exports, disclosure/support files, a real offline verification run,
and deterministic release packaging/readiness tools.

## Evidence status

- software regression and packaging behavior: currently verified;
- automatic benchmark integrity: 120/120 verified;
- benchmark task/Gold review: 120/120 primary decisions and a 30/30 stratified repeat
  check completed, with zero stale records and a hashed 194-record audit export;
- reviewer boundary: both passes use the same pseudonymous reviewer, so the evidence
  supports task/Gold verification but not independent inter-rater reliability;
- offline experiment plumbing: 360/360 verified, explicitly mock/non-formal;
- language-model comparative effectiveness: not established by this package;
- musical/aesthetic quality: not established;
- cross-host support: MuseScore bridge exercised, Sibelius not verified;
- public release reproducibility: repository and `v1.0.0` release independently verified;
  archival reproducibility remains blocked until a permanent DOI exists.

## Honest readiness verdict

`draft_prepared = true`  
`submission_ready = false`

The remaining submission blocker is the author-owned permanent archive and DOI action.
The strict verifier is designed to prevent accidental submission while that field is
incomplete.

The ordinary submitted application does not need to expose the benchmark-review screen.
The Windows package hides that route by default; the source distribution retains it as an
explicit research/reproducibility tool enabled with
`VITE_SERA_ENABLE_RESEARCH_REVIEW=true`.

## Final local delivery evidence

- Windows packaged smoke: passed for backend readiness, launcher, Electron, frozen review
  evidence and source-preserving compound/meter/voice regressions.
- Windows x64 portable SHA-256: `66052a05c9f526b0dc44d125d0bc1449998cc8db7b3b53876c7cb0a5b9b7b756`.
- Compatibility launcher SHA-256: `b5dd21e4e49022a0342f1178e843c0d6b662256ef49bcf3d19a5c25e5992fa9a`.
- Backend SHA-256: `f21e22f80d27746f8b110b1c4de2f3955ae8352534bad0ca6c667669a547e957`.
- Source and manuscript/reviewer ZIP SHA-256 values are recorded in the external
  `paper/softwarex/release/release_manifest.json` so the archives do not contain
  self-referential hashes.
- Both archives pass CRC inspection, include the frozen human-review summary/manifest,
  and exclude `.env` plus `node_modules`.

## Recommended final release sequence

1. Connect the repository to Zenodo, archive `v1.0.0`, and mint the DOI.
2. Insert the DOI in publication metadata, C3/S3, and the availability statement.
3. Rebuild the manuscript and both deterministic ZIP archives.
4. Run the strict submission verifier and confirm the current SoftwareX template.
5. The corresponding author completes the SoftwareX upload and declarations.
