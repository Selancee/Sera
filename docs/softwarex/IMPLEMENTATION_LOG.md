# SoftwareX implementation log

## 2026-08-23 - Phase SX1: requirements and repository audit

- Verified the current SoftwareX scope, 3000-word manuscript plus public open-source
  distribution requirement, OSP v4 structure and reviewer software checks.
- Audited canonical score, patch, validation, transaction, provider, evaluation,
  desktop and host-bridge paths.
- Found no root software license and a non-public configured GitHub URL; recorded both
  as release blockers.

## 2026-08-23 - Phase SX2: release metadata, rights and documentation

- Added MIT license, CFF, CodeMeta, changelog, contribution/security guidance and
  direct-dependency license/notice generation.
- Added installation, user, API and reproducibility manuals plus a requirements matrix
  and machine-readable publication metadata.
- Aligned Python/frontend/Electron/backend publication versions at dev.14 semantics.

## 2026-08-23 - Phase SX3: verification and manuscript assets

- Ran core benchmark validation (120/120; 120 pending human review).
- Created and reproduced `softwarex_verification_120_v1` (360/360, 0 errors,
  mock/non-formal).
- Passed 350 Python tests, 108 frontend tests, Vite build and dev.14 packaged runtime
  smoke.
- Created a SoftwareX v4-structured Markdown/LaTeX manuscript, line-numbered DOCX,
  architecture diagram in Mermaid/SVG/PNG/PDF, and submission statements.
- Local LaTeX PDF remains unbuilt because TeX Live is absent and bundled Tectonic's
  initial package fetch stalled; this does not affect the validated DOCX/source assets.

## 2026-08-23 - Phase SX4: release gates and archives

- Added draft/submission package verifier with tests, manuscript limits, version/license
  checks and explicit author-owned blockers.
- Added allowlisted deterministic archive export with secret/build/dependency exclusion,
  per-file hashes and archive SHA-256.
- Draft verifier passes; strict submission profile intentionally fails until public
  repository/tag/DOI, author/support data and license-owner confirmation are supplied.

## 2026-08-23 - Phase SX5: traceable human-review workspace

- Added a local desktop review workspace for all 120 core tasks without restoring the
  deprecated internal score renderer or manual notation controls.
- Added immutable task evidence, deterministic event diffs, host-openable source and
  expected MusicXML, primary/secondary roles, four-dimensional ratings, bounded issue
  codes, append-only JSONL persistence, progress/category summaries and JSON/CSV export.
- Added separate benchmark-repair and aesthetic-calibration gates. The aesthetic gate
  requires at least 20 primary reviews and at least 20% explicit musical-validity
  failures; scope/Gold/constraint errors alone cannot activate it.
- Documented a 120-task primary review plus 30-task stratified second-review protocol
  and a conditional 24-pair blinded preference-calibration cycle.
- Verified review evidence for all 120 tasks, core benchmark integrity (120/120), six
  focused backend tests, three rendered-component tests, 356 Python tests, 111 frontend
  tests in 71 files, a 215-module production build and a real local UI save/next-task
  flow. The isolated browser run recorded no console warnings or errors.
- Built the isolated `dist_desktop/release-dev14-review/win-unpacked/Sera.exe` package.
  Packaged backend, launcher and Electron health smoke passed; the frozen review API
  returned 120 total tasks and all 15 pitch-transposition tasks.
- Updated `run_app.bat` to prefer the review-enabled isolated package while retaining
  the previous dev.14 package as a fallback.
- No task has been marked human verified by this implementation work; the formal review
  count remains 0/120 until a musician/reviewer completes the interface.

## 2026-08-23 - Phase SX6: host-semantic benchmark correction

- Replaced the ambiguous first meter task with a visible and deterministic 4/4-to-3/4
  structural edit: six final-beat events are deleted and all remaining pitches and
  durations are preserved.
- Fixed repeated MusicXML dynamics and tempo placement, then regenerated all 20 source
  and 110 expected host files from canonical ScoreDocuments.
- Extended benchmark verification beyond parseability: checked-in MusicXML is now
  re-imported, compared against canonical JSON and evaluated against the task's exact
  constraints. Core remains 120/120 valid.
- Added task-fingerprint invalidation for stale human decisions. Old decisions remain
  in the append-only audit file but cannot silently validate a revised benchmark item.
- Passed 359 Python tests, 111 frontend tests and a 215-module production build. A real
  MuseScore Studio 4.5.2 render and the frozen backend both confirmed 4/4 -> 3/4, six
  deletions, 19 output events and only two serialized `mf` marks.
- Built the isolated `release-dev14-meterfix` desktop package; formal human review of
  the revised task remains required.

## 2026-08-23 - Phase SX7: reviewer-facing task-code contract

- Added a Chinese standards table for all ten task-code families to the desktop review
  workspace, benchmark card and human-review protocol. Numeric suffixes are now plainly
  identified as task serials, not measure numbers or expected diff counts.
- Added per-task Chinese explanations derived from deterministic constraints and refusal
  reasons. `conflict_001` now states that safe refusal, an unchanged expected host file
  and zero event-level changes are the required result.
- Passed five focused review tests, all 113 frontend tests in 71 files, a 215-module
  production build and core benchmark validation at 120/120. Rendered local QA verified
  the standards interaction and `conflict_001` evidence with no console warnings/errors.
- Prepared the isolated `release-dev14-standards-final` desktop output and updated launchers to
  prefer it. Its frozen backend passed health, 120-task summary and `conflict_001`
  refusal/zero-diff smoke; this explanatory change does not alter task data or formal
  review status.
- Refreshed deterministic SoftwareX source/manuscript archives. Draft verification
  passed; public repository/tag/DOI, author/support metadata and copyright-owner MIT
  confirmation remain submission blockers.

## 2026-08-23 - Phase SX8: explicit Gold-review execution boundary

- Diagnosed the reported `conflict_005` “model rejection” as an interpretation problem:
  the research-review workspace does not call a provider, and this task's Gold contract
  intentionally requires refusal with an unchanged score.
- Added explicit no-LLM, Gold-only and non-provider-failure labels to the header, task
  metadata, contract badge, refusal explanation and host-artifact instructions. Updated
  the benchmark card and review protocol with the same boundary.
- Passed five focused tests, all 113 frontend tests, production build, 120/120 benchmark
  validation and rendered `conflict_005` QA without console errors. Prepared the isolated
  `release-dev14-review-clarity` package and passed frozen backend health/refusal smoke.
- Formal review progress remains four compliant primary decisions; no decision or task
  definition was silently changed by this UI clarification.

## 2026-08-23 - Phase SX9: deterministic notation routing and `dynamics_001` repair

- Reproduced `dynamics_001` against the configured desktop provider: the original
  interactive path took 34.818 seconds and two DeepSeek attempts because the first
  proposal required model repair.
- Routed explicit event-level dynamics/articulation commands through the local strict
  patch compiler before remote planning, while retaining live LLM routing for broader
  edits and leaving all three formal experiment conditions unchanged. DeepSeek thinking
  is now disabled only for bounded patch proposal and repair calls.
- Added the task's omitted `preserve_duration` constraint. The Gold host output emits
  `f` at the third note and restores `mf` at the fourth, so only the requested note is
  affected by the persistent dynamic marking.
- Passed 16 focused generator/API tests, all 150 SeraEdit tests and core benchmark
  validation at 120/120. The frozen backend regression returned a valid one-element
  patch in 0.451 seconds with no remote provider call.
- Built `dist_desktop/release-dev14-dynamicsfix/win-unpacked/Sera.exe` and updated the
  normal launcher to prefer it without deleting prior fallback packages. Human review
  of `dynamics_001` remains pending.

## 2026-08-23 - Phase SX10: executable `key_001` semantics and review evidence

- Diagnosed the reported failure as two independent product defects rather than a bad
  Gold fixture: the Agent compiler lacked `change_key_signature`, and global key rows
  were rendered without their before/after values.
- Added strict local-first compilation for explicit whole-score key-signature changes,
  preserving the existing transaction and validation boundary. The exact `key_001`
  request now changes C major to G major while preserving all 16 event pitches.
- Updated the review UI to display global key/meter values. Rendered QA showed
  `C major -> G major` with no browser console warnings or errors.
- Passed 22 focused tests, all 152 SeraEdit tests, all 114 frontend tests in 71 files,
  a 215-module production build and core validation at 120/120. The frozen packaged
  regression completed in 0.396 seconds with one global changed element and a valid
  preview.
- Built `dist_desktop/release-dev14-keyfix/win-unpacked/Sera.exe` and made `run_app.bat`
  prefer it. This product repair does not alter formal experiment conditions or count
  `key_001` as human reviewed.

## 2026-08-24 - Phase SX11: global-property scope promotion regression

- Reproduced the exact Chinese M1-M2 desktop request against the live `keyfix` package:
  it called DeepSeek for 2.253 seconds and returned the obsolete unsupported-key refusal.
- Resolved explicit key-signature-only edits to an auditable whole-score target while
  retaining the requested scope in provenance and preserving every note pitch. Local-
  first routing now follows the resolved patch instead of the incoming host selection.
- The proposal UI now exposes the scope promotion, labels the operation as whole-score,
  and reports one global change rather than zero ordinary event changes.
- Passed 25 focused tests, all 155 SeraEdit tests, all 115 frontend tests in 71 files,
  production build and core benchmark validation at 120/120. Rendered QA had no console
  warnings/errors; the frozen exact-request smoke passed in 0.335 seconds.
- Built `dist_desktop/release-dev14-keyscopefix/win-unpacked/Sera.exe` and updated the
  launcher preference. Formal experiment conditions and human-review counts are unchanged.

## 2026-08-24 - Phase SX12: complete product-runtime acceptance and review evidence

- Added a resumable product-level acceptance runner that sends every benchmark instruction
  through the same `generate_patch_with_runtime` entrypoint used by the Agent workflow,
  then exercises dry-run validation, committed transactions, deterministic constraints and
  MusicXML export/re-import. Gold patches are excluded from generation and used only by the
  deterministic evaluator.
- Preserved the first honest baseline (`32/120` passed) and repaired the strict local compiler,
  semantic inserted-event comparison and Chinese instruction parsing until the complete core
  set ran successfully. The final replay executed 120 tasks in English and Chinese for three
  repetitions: `720/720` passed, `0` failed, `60` correct refusals, `0` unsafe executions,
  MusicXML validity `1.0`, protected-scope preservation `1.0`, and all `240/240` repeated
  task-language groups produced identical patch and post-score fingerprints.
- A separate cross-language audit then found 22 false-positive differences hidden by the
  original constraints: Chinese `保持音高` matched the tenuto keyword `保持音`. Tightening
  this token to `保持音记号` removed the unintended articulations. A fresh v2 replay again
  passed `720/720`, and now all `120/120` task groups have equivalent patch semantics and
  identical final-score fingerprints across English and Chinese.
- Added runtime-failure-first filtering and per-language host-output buttons to the human-review
  workspace. Every executable task has a compact openable English and Chinese result; expected
  refusals deliberately open the unchanged source. Review decisions remain append-only and are
  not inferred from automatic acceptance.
- Created `experiments/softwarex_runtime_acceptance_720_v1`: hashes for all 1,380 raw/host
  evidence files, 38 representative files, and 220 compact host outputs used by the packaged
  review workspace. Frozen backend specifications now bundle this snapshot.
- Passed all 163 SeraEdit tests and all 373 project Python tests, all 116 frontend tests in
  71 files, the 215-module production build, and core benchmark validation at `120/120`.
  Rendered QA verified the 120/120 summary, zero-result failure filter, six-run task badges,
  correct refusal wording, bilingual refusal artifacts and an empty warning/error console.
- Built `dist_desktop/release-dev14-runtimeacceptance/win-unpacked/Sera.exe` and made the
  normal launcher prefer it. The enhanced frozen smoke requires 120 passed tasks, 720 runs
  and a successfully prepared Chinese runtime MusicXML before it can pass; backend, legacy
  launcher and Electron lifecycle smoke all passed.
- Rewrote the historically corrupted human-review protocol in valid UTF-8 and regenerated
  the DOCX plus deterministic source/manuscript archives. Draft package verification passed.
- This is labeled `product_runtime_acceptance_non_formal`, `paper_model_result_eligible=false`
  and `gold_used_for_generation=false`. It proves deterministic product execution and regression
  coverage; it is not remote-LLM accuracy, aesthetic quality evidence or a substitute for human
  review. Formal three-condition experiments and author-owned publication metadata remain open.

## 2026-08-25 - Phase SX13: explicit instruction localization and widened host-selection evidence

- Reproduced the reported `compound_001` defect with host measures 2-3: the old local
  compiler interpreted "final two notes" over the entire host selection and targeted
  `s007_m3_rh_3`/`s007_m3_rh_4` instead of measure 2.
- Added deterministic English/Chinese extraction of explicitly named measures and staffs.
  Interactive generation now intersects this semantic location with the host-owned scope.
  It may narrow authorization but cannot expand it; a named unselected location fails closed.
  Requested, effective and excluded host scopes are retained in patch provenance. Global
  key/time properties retain their separately audited whole-score promotion behavior.
- Applied the same resolution before local-rule and live-LLM planning. Added API, transaction,
  stable-event-ID, out-of-selection, bilingual and provider-prompt regressions. The exact
  `compound_001` M2-M3 request now changes only `s007_m2_rh_3` and `s007_m2_rh_4`;
  measure 3 has zero changed events.
- Extended runtime acceptance with `--host-scope-mode expanded_adjacent`. The new
  `runtime_acceptance_core_host_scope_v1_20260825` run passed 240/240 bilingual runs.
  Expansion was applicable in 174 runs and all 174 passed; 66 non-explicit/global/no-adjacent
  runs were recorded without artificial widening. The ordinary repeated baseline
  `runtime_acceptance_core_bilingual_r3_v3_20260825` also passed 720/720 with all
  reproducibility and cross-language output rates at 1.0.
- Created publication snapshots `softwarex_runtime_acceptance_720_v2` (1,380 hashed raw/host
  files) and `softwarex_host_scope_robustness_240_v1` (460 hashed raw/host files). Updated
  the package verifier, reproducibility protocol, user/API manuals and manuscript; draft
  verification passes with a 1,637-word main text.
- Passed 171 SeraEdit tests, all 381 Python tests, 116 frontend tests in 71 files, the
  215-module production build and core benchmark validation at 120/120. Built
  `dist_desktop/release-dev14-scopefix/win-unpacked/Sera.exe`; packaged backend, compatibility
  launcher and Electron lifecycle smoke passed. Frozen HTTP smoke independently replayed
  host M2-M3 to effective M2 and confirmed `measure_3_changed=false`.
- Automatic evidence does not mark any benchmark task as human reviewed. All 120 remain
  pending review, and remote-model accuracy/artistic quality remain separate experiments.

## 2026-08-26 - Phase SX14: source-preserving product acceptance hardening

- Audited all 110 expected-success benchmark tasks through the real MuseScore delivery boundary.
  The previous acceptance runner exported a regenerated canonical score and concealed 50 source-
  preserving failures. The corrected runner now patches the original MusicXML and evaluates only
  the re-imported host output.
- Implemented host-preserving rhythm, voice, tie/slur, beam, meter and safe structural deletion;
  stabilized event IDs across deletion and restored chord anchors where necessary. Fixed persistent
  dynamic restoration after a replay exposed 17 protected-scope contaminations.
- The frozen exact replay now passes 720/720 bilingual repeated runs, including 660/660 successful
  host exports, 60 correct refusals, zero unsafe executions, and 1.0 validity, constraint and complete
  preservation rates. The widened-scope replay passes 240/240 with 220/220 host exports and all
  174 applicable scope expansions localized correctly.
- Publication snapshots were refreshed as `softwarex_runtime_acceptance_720_v3` and
  `softwarex_host_scope_robustness_240_v2`. The package verifier now hard-requires their host-export
  counts and preservation rates instead of accepting canonical-only evidence.
- Passed 397 Python tests, 117 frontend tests, production build, draft package verification and the
  complete Windows package smoke. Frozen smoke independently commits and re-imports `meter_001` as
  3/4 with 19 events and no constraint failures.
- Human review remains 0/120, and formal provider experiments, public repository, immutable tag,
  archive DOI and author-owned publication metadata remain outside this deterministic repair.

## 2026-08-26 - Phase SX15: real desktop meter-scope and frozen-evidence closure

- Reproduced a packaged-only `meter_001` failure hidden by benchmark-canonical scope. MuseScore sent
  M1-M3, the planner generated the correct meter/deletion operations, but strict preview rejected the
  non-whole-score patch before producing a diff.
- Promoted every mixed patch containing a global key/meter operation to auditable whole-score scope;
  event operations remain bound to explicit stable IDs. Added unit and API regressions for the real
  host selection and made packaged smoke require the same M1-M3 input.
- Prevented mutable development replays from replacing the curated 720-run human-review snapshot or
  pairing a 120-run summary with six-run metrics.
- Rendered QA showed `验证通过`, six deletions, one global change and successful host revision 1 with
  an empty warning/error console. Frozen smoke independently returned 3/4, 19 events and no constraint
  errors. All 399 Python tests, 117 frontend tests, production build and 120/120 replay passed.

## 2026-08-26 - Phase SX16: loss-tolerant host-session delivery

- Reproduced a real mismatch where MuseScore Bridge held the new `rhythm_001` revision-0 session but
  Sera Desktop remained on an older revision-3 session after a renderer notification was missed.
- Added backend compensation polling, session-bound proposals and stale-async-result rejection. A
  proposal can no longer remain applicable after the host session changes.
- Added non-mutating reactivation of an existing notation session and integrated it into MuseScore
  Bridge 0.3.3. Pressing the Bridge open button on revision 0 now re-focuses Sera on that exact
  session instead of only displaying an instruction or creating a duplicate session.
- Passed all 400 Python tests, 119 frontend tests and the 215-module build. Frozen runtime inspection
  confirmed the activation route, preserved revision 0/source artifact, and rendered the exact
  M1-M2 session in the canonical packaged desktop app. Package hashes are recorded in the ICMC
  implementation log.
- This improves reproducibility of the human-review workflow but does not alter benchmark outputs,
  formal model comparisons or pending human musical-quality judgments.

## 2026-08-26 - Phase SX17: part-wide MusicXML voice interoperability

- Diagnosed a false-positive acceptance gap in `voice_001-015`: canonical re-import accepted
  staff-local `<voice>1/2</voice>` reuse, while MuseScore treated those values as part-wide logical
  voices and could remap unrelated measures or staves.
- Implemented explicit local-to-host voice mapping (staff 1: 1-4, staff 2: 5-8), inverse import
  mapping, and legacy lower-staff normalization during source-preserving voice patches. The mapping
  is backed by W3C MusicXML part-scope semantics and observed MuseScore 4 export output.
- Refreshed only derived MusicXML assets from the unchanged canonical benchmark JSON, added focused
  regressions, and re-ran the complete product acceptance rather than relabeling old evidence.
- `runtime_acceptance_core_bilingual_r3_v4_20260826` passed 720/720 runs with 660/660 source-
  preserving host exports. `runtime_acceptance_host_roundtrip_scope_v2_20260826` passed 240/240
  runs with 220/220 exports and all 174 widened selections localized correctly.
- Publication evidence is now frozen as `softwarex_runtime_acceptance_720_v4` (1,380 hashed files)
  and `softwarex_host_scope_robustness_240_v3` (460 hashed files). Draft package verification and
  all 402 Python tests pass.
- This closes host voice-lane interoperability for the benchmark but remains non-formal product
  evidence. Formal provider comparison, public release metadata and human musical review remain
  separate submission requirements.
# 2026-08-27 - Phase SX18: completed human evidence and release-mode separation

- Verified the live desktop review summary rather than trusting a UI counter: 120/120
  current primary reviews, 30/30 stratified repeat checks, zero stale records, zero
  remaining tasks, and all ten categories complete.
- Exported the append-only audit history to
  `experiments/softwarex_human_review_120_v1`: 194 JSON/CSV records plus a summary and
  SHA-256 manifest. Both passes use `reviewer-01`, so the manuscript explicitly avoids
  an independent inter-rater or universal aesthetic-quality claim.
- Added `scripts/export_human_review_evidence.py`, validation tests, and strict package
  checks that reject incomplete or hash-drifted human evidence.
- Made the review workspace optional publication tooling. Ordinary Agent builds hide
  it; a source reviewer can opt in with `VITE_SERA_ENABLE_RESEARCH_REVIEW=true`.
- Updated the SoftwareX manuscript, reproducibility protocol, user manual, requirements
  matrix, completion report, checklist and verification report. Full regression passes
  404 Python tests and 120 frontend tests in 72 files; the production build transforms
  216 modules.
- The remaining submission blockers are author/legal metadata, a reviewed release
  commit/tag, public repository availability, an archive DOI, final template/PDF check,
  and the corresponding author's manual Editorial Manager submission.

# 2026-08-27 - Phase SX19: packaged release and reviewer-archive closure

- Rebuilt the ordinary Windows/Electron distribution with the research-review entry
  disabled by default. The packaged backend, compatibility launcher and Electron process
  all passed real startup/health smoke with backend-readiness waiting enabled.
- Replayed the formerly failing host-boundary cases from the packaged build. The expanded
  M2-M3 selection for `compound_001` changed only the two explicit M2 events; `meter_001`
  exported/re-imported as 3/4 with six intended deletions; `voice_010` and `voice_004`
  changed only staff-1 measure 3 while staff-2 MusicXML lanes 5/6 remained stable.
- Added the frozen human-review summary and SHA-256 manifest to both the source archive and
  the manuscript/reviewer archive. Both ZIPs pass CRC checks and contain no `.env` or
  `node_modules` entries.
- Final local archive hashes are recorded outside the archives in
  `paper/softwarex/release/release_manifest.json`, avoiding a self-referential hash.
  The unpacked desktop and backend hashes are
  `fd09c1e98dbeafa5362d3534dee2ecbcd45ac2da7193804ec3c75f8de9ec087a`
  and `d682393db5a8fa7bb5bbcf92f93f0780adf6dbe1bc6703bbbcbd86efb71304e9`.
- Focused export/evidence tests pass 5/5 and the draft SoftwareX verifier passes. The
  strict profile still fails only on the seven author-controlled public-release and
  identity/legal metadata gates recorded in `submission_verification.json`.

# 2026-08-27 - Phase SX20: private-upload baseline

- Re-ran the release baseline before GitHub upload: 404 Python tests, 120 frontend tests
  in 72 files, the 216-module production build, 120/120 core benchmark validation, the
  V0.93 source evaluation, the SoftwareX draft verifier and complete packaged runtime
  smoke all passed.
- Recorded the exact checks and the optional source-renderer limitation in
  `BASELINE_REPORT_2026-08-27.md` rather than converting that unavailable optional path
  into a false success.
- Audited the existing remote before upload. Authenticated Git can read it while anonymous
  HTTPS returns 404, confirming the requested private/non-public state.
- Expanded ignore rules for local caches, runtime sessions, user projects, build archives
  and old distribution bundles. Frozen SoftwareX evidence is explicitly allowlisted.
- Staged-content scans found no API/private key material and no file at or above 100 MB.

# 2026-08-27 - Phase SX21: private GitHub preservation upload

- Committed the tested release candidate as `7ee92238f603df0d560f555cad7517a233b0bae3`
  (`Prepare SeraEdit SoftwareX research baseline`) and pushed it to the existing
  `origin/main` branch.
- The push completed from `b4eb139` to `7ee9223`. Anonymous HTTPS still returns 404 while
  authenticated Git resolves the new branch head, confirming that the repository remains
  private as requested.
- No public release, immutable release tag, archive DOI or visibility change was made.
  Consequently, private preservation is complete while the SoftwareX public-release gate
  intentionally remains unsatisfied.

# 2026-08-27 - Phase SX22: reviewer-first reproducibility and rendered manuscript

- Added a one-command, offline reviewer demonstration covering transposition, dynamics,
  key signature, meter/deletion, staff-local voice movement and expected refusal through
  the actual local product path. It passes 6/6 tasks and creates five host-openable
  MusicXML revisions without an API key, network call or Gold-assisted generation.
- Added a Windows GitHub Actions workflow for Python regression, 120-task benchmark
  validation, reviewer demonstration, SoftwareX package audit, frontend regression and
  production build. Added a tested-Windows direct-dependency constraints file and package
  metadata/installation documentation for a clean reviewer environment.
- Corrected the documented npm command order after reproducing a root-level
  `package.json` lookup failure, then added a regression assertion for both reviewer
  documents. The verified command passes 120/120 frontend tests; the build transforms
  216 modules.
- Separated immutable task-file `pending_human_review` metadata from the completed frozen
  external review evidence. Core benchmark validation now reports 120/120 automatically
  valid, zero effective human reviews pending, 120 immutable metadata flags, 120 primary
  and 30 repeat reviews, zero stale records, and the same-reviewer limitation.
- Expanded the manuscript with an evidence/claim-boundary table and reviewer reproduction
  path. The draft verifier reports 1,747 main-text words, a 105-word abstract, six
  keywords and one numbered figure.
- Compiled the SoftwareX LaTeX source with bundled Tectonic 0.17.0. The eight-page PDF was
  rasterized and inspected page by page; tables, figure, line numbers and references are
  readable, and extracted text contains no Unicode replacement characters. The DOCX was
  regenerated with three tables and one embedded figure.
- Full local evidence passes 408 Python tests, 120 frontend tests, the 216-module build,
  120/120 benchmark validation, the 6/6 reviewer demo, dependency integrity and the draft
  package verifier. These changes improve reviewer reproducibility but do not convert the
  offline rule/mock results into formal remote-model accuracy evidence.

## Remaining author-controlled work

- Supply author, affiliation, support, funding, competing-interest and CRediT metadata;
  confirm copyright/MIT release authority; approve public visibility; create the immutable
  tag; mint the archive DOI; and perform the final Editorial Manager submission.
- A paid live-model three-condition experiment remains optional and must not be started
  without an explicit model/cost decision.

# 2026-08-27 - Phase SX23: author and affiliation metadata integration

- Recorded the sole author as Yuan Gao with ORCID `0009-0005-0394-3623` in the
  manuscript, `CITATION.cff`, CodeMeta and publication configuration.
- Added the official English Zhejiang Conservatory of Music affiliation and postal
  address consistently across the Markdown and LaTeX manuscript sources.
- Recorded the author-supplied no-specific-funding status and prepared a sole-author
  CRediT statement. Updated the MIT notice to identify Yuan Gao as copyright holder,
  while retaining the explicit `license_owner_confirmed: false` publication gate.
- Did not infer a personal support email, competing-interest declaration, final CRediT
  confirmation, release authorization, repository visibility, tag or DOI. These remain
  author-controlled submission requirements.
- Recorded the supplied sole-author status separately from three still-unconfirmed
  statements: CRediT roles, competing interests, and manuscript originality/exclusive
  submission. Strict verification now fails explicitly on each missing confirmation.
- Rebuilt the line-numbered DOCX and eight-page LaTeX PDF. Structural/text extraction
  checks confirm the author, affiliation, ORCID and funding statement; selected rendered
  pages were visually inspected without layout regressions.
- Replaced an over-specific package check that required the old `Sera contributors`
  copyright string with content-based MIT validation, and added ORCID checksum plus
  CFF/CodeMeta/manuscript consistency checks. All 410 Python tests and the draft
  SoftwareX verifier pass; nine author-controlled submission gates remain, including
  separate MIT-code and CC0-benchmark rights confirmations.

# 2026-08-27 - Phase SX24: author declarations and publication metadata closure

- Recorded the author-supplied corresponding email consistently in the manuscript,
  CFF, CodeMeta, cover letter and publication configuration.
- Recorded explicit confirmation of the sole-author CRediT roles, no known competing
  interests, manuscript originality/exclusive submission, MIT code authorization and
  CC0 benchmark dedication authorization.
- Replaced declaration and cover-letter placeholders with the confirmed statements;
  retained public repository visibility, immutable tagging and archive DOI as the only
  remaining strict submission gates.
- Added support-email format and cross-file consistency validation so a malformed or
  drifting email fails package verification rather than reaching submission artifacts.
- Rebuilt and visually checked the eight-page PDF plus line-numbered DOCX. All 411 Python
  tests pass; draft package verification passes; strict verification now reports exactly
  three external blockers: public repository visibility, immutable tag and archive DOI.

# 2026-08-27 - Phase SX25: version 1.0.0 release-candidate verification

- Promoted all active Python, backend, frontend, Electron, CFF, CodeMeta, manuscript and
  archive-version fields from `1.0.0-dev.14` to coordinated release version `1.0.0`.
- Added the final changelog entry and Electron package description, author and MIT metadata.
  Historical dev.14 implementation logs and the dated baseline report remain unchanged.
- Passed 411 Python tests, 120 frontend tests, the 216-module production build, 120/120
  core benchmark validation and the 6/6 offline reviewer demonstration.
- Rebuilt the backend, compatibility launcher and Electron app from source. Packaged
  backend, frontend, launcher and Electron health/startup/shutdown smoke passed, including
  compound, meter and staff-local voice MusicXML regressions.
- Built `Sera-1.0.0-x64.exe` (234,325,156 bytes; SHA-256
  `66052a05c9f526b0dc44d125d0bc1449998cc8db7b3b53876c7cb0a5b9b7b756`) as the portable
  release asset. It uses Electron's default icon because no project-owned icon asset is
  present; this is a visual limitation, not a runtime failure.
- Rebuilt and structurally checked the DOCX plus eight-page PDF at release version 1.0.0.
  Public visibility, tagging and GitHub Release creation remain pending the external step.

# 2026-08-27 - Phase SX26: authorized public-release metadata closure

- Applied the author's explicit authorization to change the GitHub repository from private
  to public and verified anonymous API visibility at `https://github.com/Selancee/Sera`.
- Bound the manuscript, availability statement and publication configuration to the
  immutable `v1.0.0` release URL and the versioned Windows x64 asset URL. No DOI was
  invented; C3/S3 and the archive metadata remain explicit Zenodo placeholders.
- Rebuilt the line-numbered DOCX and eight-page PDF after link replacement. Draft package
  verification passes, while strict submission verification now reports exactly one
  author-owned blocker: `permanent archive DOI is missing`.
- The verified public-release payload comprises the portable Windows executable plus
  deterministic source and manuscript/reviewer archives. Git tagging and GitHub Release
  upload are the next authorized external actions.

# 2026-08-27 - Phase SX27: public v1.0.0 release publication and independent verification

- Created and pushed annotated tag `v1.0.0` at commit
  `b23afcf08c26c46625fc3f24d82882495de9348f`.
- Published `https://github.com/Selancee/Sera/releases/tag/v1.0.0` as a non-draft,
  non-prerelease GitHub Release with the Windows portable executable, deterministic source
  ZIP, SoftwareX manuscript/reviewer ZIP, `SHA256SUMS.txt`, and the full release manifest.
- Queried the repository and release through unauthenticated GitHub API requests. All five
  assets report `uploaded`, and every GitHub SHA-256 digest matches its local artifact.
- The immutable public software release is complete. Zenodo connection, DOI minting and
  final journal-system submission remain under the corresponding author's control.

# 2026-08-27 - Phase SX28: reserved Zenodo DOI integration and publication gate

- Recorded reserved DOI `10.5281/zenodo.22128976` and Zenodo record `22128976` in
  `publication.yml`, CFF, CodeMeta, manuscript C3/S3 tables, availability statement,
  cover letter, reproducibility notes, readiness matrix and submission checklist.
- Added explicit `archive_status: reserved` and `archive_published: false` metadata.
  The strict verifier now rejects a reserved DOI until the deposit is actually public,
  while separately validating DOI syntax, canonical URL and cross-file consistency.
- Added three archive-gate regression tests. The focused verifier suite passes 11/11;
  the complete Python suite passes 414/414; the core benchmark validates 120/120 with
  frozen human-review evidence present.
- Rebuilt the line-numbered DOCX and eight-page LaTeX PDF. The DOCX contains the DOI,
  the PDF compiles successfully with the existing minor box-spacing warnings, and both
  readiness JSON reports were regenerated.
- Preserved the already published and Zenodo-uploaded exact `v1.0.0` source ZIP instead
  of silently replacing it with a post-release metadata snapshot. Its SHA-256 remains
  `7ae6a9ab20c29279fb04872fee8fa549d4f6a361dba571821c38c608c4b4e0e6` and CRC passes.
- Unresolved: the corresponding author must review and publish Zenodo record `22128976`.
  After publication, change the archive state to `published`, replace reserved-status
  wording, rebuild final manuscript assets, and require strict verification exit 0.
- Paper impact: C3/S3 and citation metadata now carry the real reserved DOI without
  overstating public availability; no experimental metrics or scientific claims changed.

# 2026-08-28 - Phase SX29: public Zenodo archive and strict submission readiness

- Published Zenodo software record `22128976`. Version DOI
  `10.5281/zenodo.22128976` now resolves publicly to SeraEdit 1.0.0; concept DOI
  `10.5281/zenodo.22128975` represents all versions.
- Updated `publication.yml` to `archive_status: published` and
  `archive_published: true`, and propagated truthful public-archive wording through the
  manuscript, cover letter, availability statement, reproducibility notes, final report,
  requirements matrix and checklist.
- Rebuilt the DOCX and eight-page PDF successfully. Added tested
  `--preserve-existing-source` export behavior so post-publication manuscript rebuilds
  cannot silently replace the immutable source ZIP.
- Preserved source ZIP SHA-256
  `7ae6a9ab20c29279fb04872fee8fa549d4f6a361dba571821c38c608c4b4e0e6`. The rebuilt
  manuscript/reviewer ZIP digest is stored only in the external
  `release_manifest.json` to avoid self-reference.
- Verification: all 420 Python tests passed; exporter tests 5/5; core benchmark 120/120;
  both ZIP CRC checks passed; draft and submission package verifiers exited 0 with no
  automated blocker.
- Remaining scope is author-controlled: final visual manuscript check, current template
  and APC confirmation, exact manuscript approval, and Editorial Manager upload.
- Paper impact: the permanent-archive claim is now public and verifiable. No research
  result or model-performance claim changed.

# 2026-08-28 - Phase SX30: Editorial Manager preparation and live-guide alignment

- Verified the current official SoftwareX submission entry and Guide for Authors.
  Aligned the automated readiness limits to 4000 main-text words, six figures, a
  250-word abstract, 1-7 keywords, and 3-5 highlights of at most 85 characters.
- Added a field-by-field Editorial Manager preparation sheet and corrected the one
  remaining stale reserved-DOI sentence in the standalone availability statement.
- Added a tested, reproducible Word-attachment builder for the cover letter and four
  declarations required during submission; the Markdown files remain the auditable
  source of those attachments.
- Inserted the mandatory generative-AI disclosure into the Markdown and LaTeX
  manuscript sources before the references, regenerated the line-numbered DOCX, and
  compiled the final nine-page PDF with Tectonic 0.17.0. Final visual inspection remains
  author-controlled.
- Focused tests passed 15/15, the complete Python suite exited 0, strict submission
  verification exited 0, and both final ZIPs passed CRC checks. The preserved source
  digest remains `7ae6a9ab20c29279fb04872fee8fa549d4f6a361dba571821c38c608c4b4e0e6`;
  the rebuilt manuscript/reviewer digest is recorded only in the external release
  manifest and the top-level research log, avoiding a self-referential archive hash.
- Final external actions remain author-controlled: account sign-in, transmission of
  identity/files, review of the assembled submission and APC, and final submission.
- Paper impact: no experimental metric, statistical result, or model-performance claim
  changed.

# 2026-08-28 - Phase SX31: submission-file privacy hardening

- Audited the six Word upload files and final PDF for hidden creator, last-modifier,
  application, timestamp, comment, custom-property, local-path and document-generation
  metadata. The original generated Word packages contained authoring-tool/date traces;
  these were removed without deleting visible publication content.
- Added `scripts/submission_metadata.py`, integrated deterministic DOCX sanitization into
  both document builders, cleared PDF producer/date metadata in the LaTeX source, and
  made submission privacy a blocking check in the strict package verifier.
- Rebuilt all upload documents. The seven-file privacy audit reports no findings while
  intentionally retaining the confirmed author, affiliation, corresponding email,
  ORCID, public release links and required generative-AI disclosure.
- Added a submission privacy report and regression coverage. The focused suite passed
  19/19, the complete Python suite passed 424/424, and strict SoftwareX verification
  exited 0 with 41/41 required files and no automated blocker.
- Paper impact: no experiment, metric or scientific claim changed; only submission
  metadata hygiene and auditability changed.

# 2026-08-29 - Phase SX32: clean-checkout Research CI regression repair

- Traced the eight GitHub Research CI failure notifications to one repository-state
  mismatch: `test_runtime_acceptance_evidence_export.py` read an ignored local experiment
  directory that is unavailable in a clean GitHub Actions checkout.
- Replaced the hidden local-data dependency with a small generated fixture that exercises
  the exporter deterministically, and added a separate integrity test for the tracked
  `softwarex_runtime_acceptance_720_v4` publication snapshot.
- The repair changes test inputs only. It does not alter the published Zenodo archive,
  the SoftwareX submission files, runtime evidence, experimental metrics or scientific
  claims.
