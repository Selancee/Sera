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
  Zenodo version DOI `10.5281/zenodo.22128976` is publicly registered and resolves to
  the immutable SeraEdit 1.0.0 source archive.

## Honest readiness verdict

`draft_prepared = true`  
`submission_ready = true`

No automated package blocker remains after publication of Zenodo record `22128976`.
The strict verifier confirms the public archive, citation propagation, technical
evidence and completed benchmark review. The manuscript was submitted to SoftwareX on
28 August 2026 as `SOFTX-D-26-01135` and was last confirmed **Under Review** on
3 September 2026. Future revision decisions and any applicable APC arrangement remain
author-controlled.

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

## Remaining author-controlled sequence

1. Monitor Editorial Manager and the corresponding-author mailbox for reviewer action.
2. Preserve the submitted manuscript and immutable `v1.0.0`/Zenodo snapshot.
3. Evaluate and prepare any requested revision without rewriting historical evidence.
4. Reconfirm the applicable APC and funding arrangement if the manuscript is accepted.
