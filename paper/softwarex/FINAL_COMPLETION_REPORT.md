# SoftwareX preparation completion report

## Delivered

The repository now contains an independent SoftwareX release track for SeraEdit
`1.0.0-dev.14`: open-source/citation metadata, rights inventory, research-software
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
- public/archival reproducibility: blocked until public tag and DOI exist.

## Honest readiness verdict

`draft_prepared = true`  
`submission_ready = false`

The remaining blockers require author identity, legal confirmation, public-release and
archive actions. The strict verifier is designed to prevent accidental submission while
those fields are incomplete.

The ordinary submitted application does not need to expose the benchmark-review screen.
The Windows package hides that route by default; the source distribution retains it as an
explicit research/reproducibility tool enabled with
`VITE_SERA_ENABLE_RESEARCH_REVIEW=true`.

## Final local delivery evidence

- Windows packaged smoke: passed for backend readiness, launcher, Electron, frozen review
  evidence and source-preserving compound/meter/voice regressions.
- Desktop SHA-256: `fd09c1e98dbeafa5362d3534dee2ecbcd45ac2da7193804ec3c75f8de9ec087a`.
- Backend SHA-256: `d682393db5a8fa7bb5bbcf92f93f0780adf6dbe1bc6703bbbcbd86efb71304e9`.
- Source and manuscript/reviewer ZIP SHA-256 values are recorded in the external
  `paper/softwarex/release/release_manifest.json` so the archives do not contain
  self-referential hashes.
- Both archives pass CRC inspection, include the frozen human-review summary/manifest,
  and exclude `.env` plus `node_modules`.

## Recommended final release sequence

1. Fill `docs/softwarex/publication.yml` and all bracketed manuscript/submission fields.
2. Review `git status`, the complete diff, dependencies/licenses and archive contents.
3. Run all commands in `docs/softwarex/INSTALLATION.md` and the draft verifier.
4. With explicit authorization, commit and create the release tag; never publish secrets.
5. Make GitHub public, mint the archive DOI, update metadata and rebuild both ZIPs.
6. Compile/check the final manuscript and run the strict submission verifier.
7. The corresponding author completes the SoftwareX upload and declarations.
