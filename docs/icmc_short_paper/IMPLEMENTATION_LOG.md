# SeraEdit Implementation Log

This file is append-oriented. Experimental claims must point to persisted raw outputs; mock-provider results are never formal paper results.

## 2026-08-05 — Phase 1: repository audit and scope freeze

### Completed

- Read the repository contract and audited backend, frontend, canonical score, patch, validation, provider, rendering, persistence, and evaluation paths.
- Confirmed the Workbench ScoreDocument boundary is the product editing authority.
- Recorded the additive compatibility strategy and research risks in `REPOSITORY_AUDIT.md`.
- Ran the complete pre-change backend/frontend/build baseline.

### Modified files

- `docs/icmc_short_paper/REPOSITORY_AUDIT.md`
- `docs/icmc_short_paper/IMPLEMENTATION_LOG.md`

### Tests

- Backend: 193 passed, 0 failed.
- Frontend: 90 passed, 0 failed across 65 files.
- Frontend production build: passed.

### Unresolved

- Strict SeraEdit schema, scope, fingerprint, protected-scope, transaction, and benchmark layers are not yet implemented at this log entry.
- Stable event-ID re-import and complex MusicXML notation relations require regression work.
- No live provider experiment has been run; no API key was read or stored.

### Next phase

- Implement the isolated SeraEdit domain, validation, diff, transaction, and undo core with tests.

### Paper impact

- Establishes the reproducible regression baseline and documents why product V0.7 patches cannot be treated as the paper's strict experimental representation.

## 2026-08-05 - Phase 2: strict ScorePatch transaction core

### Completed

- Added isolated `sera_edit` domain models for ScoreScope, ScorePatch 1.0.0, exact source fingerprints, deterministic operations, and event-level diff.
- Added strict schema, structural, duration, notation-relation, semantic-precondition, and protected-scope validators.
- Added atomic apply/rollback, dry-run preview, patch-level undo/redo, and bounded deterministic formatting repair.
- Unknown operation types now produce `E19 unsupported_operation`; the research path never delegates unknown operations to the legacy no-op behavior.
- Added strict local API routes: `/sera-edit/schema-validate`, `/sera-edit/preview`, and `/sera-edit/apply`.
- Restored Sera event IDs from exported MusicXML metadata during re-import.

### Modified files

- `sera_edit/domain/*`
- `sera_edit/validation/*`
- `sera_edit/execution/*`
- `sera_edit/api/routes.py`
- `benchmark/schemas/score_patch.schema.json`
- `backend/services/score_document_service.py`
- `backend/app.py`
- `tests/sera_edit/*`

### Tests

- Focused SeraEdit suite after this phase: 28 passed, 0 failed.
- Complete backend regression after all phases in this entry: 221 passed, 0 failed.
- Frontend regression: 90 passed, 0 failed across 65 files.
- Frontend production build: passed with the pre-existing large-chunk warning.

### Unresolved

- Tuplets, beams, grace notes, chord relations, and full multi-voice duration semantics need deeper validators.
- Current strict API is additive; Workbench UI has not yet been switched to these research endpoints.

### Next phase

- Expand notation operation coverage and connect the existing local Electron Workbench research mode to strict preview/apply/reject/undo.

### Paper impact

- Supplies the source-bound, protected, transactional Condition C implementation needed for the core comparison.

## 2026-08-05 - Phase 3: Benchmark Batch 1

### Completed

- Generated 5 deterministic synthetic source scores and 30 bilingual editing tasks across six categories.
- Generated 25 gold patches and 75 expected output artifacts; 5 conflict tasks require refusal and intentionally have no gold patch.
- Added task/patch schemas, benchmark card, source attribution, license, deterministic generator, and validator.
- Persisted `benchmark/validation/batch1_report.json` from a real validation run.

### Tests

- Automatic benchmark validation: 30 valid, 0 invalid.
- Every success task passed schema validation, gold transaction apply, deterministic constraints, expected fingerprint, and MusicXML round-trip.
- Human music review remains pending for all 30 tasks; automatic validation is not described as human verification.

### Unresolved

- Batch 1 is a development set, not the final 120-task core benchmark.
- Weak pickup, compound meter, multi-voice, ties/slurs, chords, ornaments, and irregular rhythms remain underrepresented.

### Next phase

- Build Batch 2 to 60 tasks with richer score structures, then complete the 120-task reviewed core split.

### Paper impact

- Validates the full benchmark asset chain while preventing premature claims about the final dataset.

## 2026-08-05 - Phase 4: three-condition mock smoke

### Completed

- Implemented separated Full-Score Rewrite, ScorePatch Only, and Sera Full condition paths.
- Added provider-neutral response metadata and a deterministic benchmark-fixture mock provider.
- Added versioned prompt hashes, deterministic task metrics, resumable JSONL execution, config snapshot, manifest, raw/normalized outputs, CSV metrics, errors, and summary.
- Ran 30 tasks x 3 conditions x 1 mock fixture provider = 90 runs.

### Tests and evidence

- Smoke execution: 90 completed, 0 runner errors.
- Raw outputs: 90; normalized outputs: 90.
- Resume check: rerunning the same experiment kept `runs.jsonl` at 90 rows and added 0 duplicates.
- Result class is hard-coded and persisted as `mock_non_formal`; `formal_results_allowed` is false.
- Mock summary numbers validate plumbing only and must not be copied into the paper as model performance.

### Unresolved

- No live provider call was made, no API key was read, and no formal experiment result exists.
- Retry/backoff, rate limiting, concurrency, formal cost accounting, paired statistics, paper assets, and anonymous export remain future phases.
- Condition A exposes current MusicXML round-trip loss for some notation fields such as dynamics; this requires a dedicated regression phase rather than metric masking.

### Next phase

- Finish provider adapters and robust formal runner controls, then execute a budgeted live smoke only when a user-supplied environment key and model configuration are available.

### Paper impact

- Demonstrates that experiment persistence and condition separation run end to end without fabricating publishable results.

## 2026-08-05 - Phase 5: MusicXML round-trip fidelity and complex notation validation

### Completed

- Replaced note-order metadata alignment with a direct MusicXML event parser so event IDs remain paired with their original note nodes across multiple voices.
- Added round-trip support for dynamics, standard direction dynamics, articulations, explicit accidentals, ties, slurs, chord membership, grace notes, tuplets, voices, rests, and beam metadata.
- Added MusicXML namespace stripping for external MusicXML documents.
- Changed same-staff multi-voice export to use independent voice timelines and MusicXML `backup` elements instead of one shared cursor.
- Added 12-division triplet export with `time-modification` and exact `1/3` duration arithmetic.
- Corrected notation normalization so grace notes do not consume duration and legacy float offsets are snapped to common rational notation positions.
- Made tie-split continuation IDs unique and traceable through `tie_origin_event_id`.
- Strengthened SeraEdit duration validation with exact coverage, internal gap reporting, voice-collision detection, pickup handling, and grace exclusion.
- Strengthened notation validation for duplicate IDs, invalid/dangling ties and slurs, malformed chords, unequal chord durations, and rest/chord collisions.
- Added semantic MusicXML round-trip fidelity validation; missing, added, or changed supported notation fields now produce `E14` and roll back the transaction.
- Preserved compatibility of old gold fingerprints by excluding newly introduced false/null default notation fields from semantic hashes.

### Modified files

- `backend/services/score_document_service.py`
- `backend/notation/duration_math.py`
- `backend/notation/notation_normalizer.py`
- `backend/notation/tie_splitter.py`
- `sera_edit/domain/fingerprints.py`
- `sera_edit/validation/duration_validator.py`
- `sera_edit/validation/notation_relation_validator.py`
- `sera_edit/validation/roundtrip_fidelity_validator.py`
- `sera_edit/execution/transaction.py`
- `scripts/validate_benchmark.py`
- `evaluation/runners/experiment_runner.py`
- `sera_edit/providers/mock_provider.py`
- `tests/sera_edit/test_musicxml_notation_roundtrip.py`
- `tests/sera_edit/test_complex_notation_validation.py`
- `tests/sera_edit/test_roundtrip_fidelity_validator.py`

### Tests and evidence

- Focused SeraEdit suite: 43 passed, 0 failed.
- Complete backend suite: 236 passed, 0 failed.
- Frontend suite: 90 passed, 0 failed across 65 files.
- Frontend production build: passed with the existing large-chunk warning.
- Batch 1 revalidation: 30 valid, 0 invalid; all 30 still await human music review.
- Fidelity v4 mock smoke: 90 completed, 0 runner errors, 0 duplicate rows after resume.
- V2 and V3 smoke directories were retained as diagnostic evidence for default-field comparison and fingerprint compatibility failures; they were not overwritten.
- Every fidelity smoke remains `mock_non_formal` with `formal_results_allowed=false` and cannot support paper performance claims.

### Unresolved

- Multiple MusicXML parts are still collapsed into the current single-piano ScoreDocument representation.
- Numbered/nested simultaneous slurs are explicitly rejected because the current event model stores one slur state per event.
- Tuplet support currently covers triplet eighth notes, not arbitrary nested tuplets.
- External host engraving details such as layout, fonts, placement, fingering, ornaments, lyrics, and proprietary MuseScore/Sibelius metadata are not yet round-trip guaranteed.
- Real MuseScore and Sibelius round-trip behavior remains unverified on the host applications.

### Next phase

- Connect strict preview/apply/reject/undo and fidelity reports to the local Electron Workbench research mode, then begin the 60-task Batch 2 with multi-voice, chord, tie/slur, 6/8, grace, and conflict cases.

### Paper impact

- Removes a major confound in Condition A/C comparison: supported notation-field loss is now measured and rejected rather than silently attributed to the language model.

## 2026-08-05 - Phase 6: local Electron strict ScorePatch workflow

### Completed

- Added a deterministic, bounded local instruction generator for major-second, semitone and octave transposition, dynamics, and staccato/accent/tenuto articulation.
- Added explicit `unsupported` and conflict `refused` outcomes; local-rule provenance is marked `formal_experiment_eligible=false`.
- Added `/sera-edit/generate-preview` to generate a strict ScorePatch and execute the complete dry-run transaction in one local request.
- Made Strict ScorePatch the default Workbench agent workflow while preserving the existing agent panel as a compatibility mode.
- Added target/protected scope controls for measures/events, staff, and voice, plus local presets for supported, compound, and conflicting instructions.
- Added ScorePatch JSON, event diff, source/post fingerprint, layered validation report, MusicXML round-trip report, and fidelity report to the Electron Workbench.
- Connected strict apply, reject, undo, and redo to the authoritative `ScoreDocument`; strict history refuses to overwrite a score after intervening edits.
- Kept display, playback, export, strict commit, and host revision export on the same canonical score state.

### Modified files

- `sera_edit/generation/rule_patch_generator.py`
- `sera_edit/generation/__init__.py`
- `sera_edit/api/routes.py`
- `tests/sera_edit/test_rule_patch_generator.py`
- `tests/sera_edit/test_api_routes.py`
- `frontend/src/api.js`
- `frontend/src/score/scoreTypes.ts`
- `frontend/src/score/seraEditResearch.ts`
- `frontend/src/score/__tests__/seraEditResearch.test.ts`
- `frontend/src/workbench/SeraEditResearchPanel.tsx`
- `frontend/src/workbench/__tests__/SeraEditResearchPanel.test.tsx`
- `frontend/src/workbench/ScoreWorkbench.tsx`
- `frontend/src/styles.css`

### Tests and evidence

- Focused SeraEdit backend suite: 49 passed, 0 failed.
- Complete backend suite: 242 passed, 0 failed.
- Frontend suite: 96 passed, 0 failed across 67 files.
- New frontend scope, history, and research-panel tests: 6 passed, 0 failed.
- Desktop launcher and packaging contract subset: 13 passed, 0 failed.
- Frontend production build: passed with the existing large-chunk warning.
- Visible Electron smoke used `benchmark/source_scores/score_001.musicxml`; no external browser was opened.
- The visible strict preview reported 8 changed events, 0 added, 0 deleted, protected-scope preservation rate 1, round-trip fidelity rate 1, and a valid MusicXML round-trip.
- The visible strict transaction committed successfully; strict undo and redo both restored the expected local score state.

### Unresolved

- The local rule generator is intentionally narrow and is not evidence of LLM instruction coverage or formal model performance.
- Strict undo/redo history is currently session-local and deliberately becomes unavailable after unrelated intervening edits.
- The current research panel shows an event-level diff and target highlight, but does not yet render a full before/after notation overlay.
- Real MuseScore and Sibelius host round trips remain unverified.
- Batch 1 still awaits human music review; the 60-task Batch 2 has not yet been generated.

### Next phase

- Build and validate Batch 2 to 60 tasks with multi-voice, chord, tie/slur, 6/8, grace-note, and conflict coverage, then add a notation before/after overlay without creating a second authoritative score state.

### Paper impact

- Supplies a local, demonstrable Condition C interface in which every proposed edit exposes its scope, structured patch, validation evidence, preservation result, fingerprints, and reversible commit state.

## 2026-08-05 - Phase 7: cumulative 60-task and Core 120 benchmark

### Completed

- Added deterministic incremental task resolution so cumulative splits reuse Batch 1 assets without copying or silently selecting duplicate task IDs.
- Added 15 synthetic source scores with 4/4 and 6/8 meters, major/minor keys, independent second voices, chords, slurs, cross-measure ties, and grace-note fixtures.
- Generated Batch 2 as a cumulative 60-task development split and Core v1 as a 120-task split over 20 source scores.
- Reached the planned exact category distribution: 15 each for pitch, rhythm, key/harmony, and voice/texture; 10 each for the remaining six categories.
- Added deterministic constraints for pitch, articulation, tie/slur, voice, grace, meter, chord pitches, and changed-element counts.
- Corrected `replace_chord` so it produces one primary note plus explicit chord tones and retains chord-group identity through MusicXML.
- Preserved grace/chord metadata for inserted notes.
- Fixed dotted-half MusicXML import labeling so 6/8 second voices survive round-trip as `dotted_half` rather than `dotted_quarter`.
- Generated UTF-8 human-review checklists and a source-score manifest; all 120 tasks remain honestly marked `pending_human_review`.
- Rewrote the benchmark README, benchmark card, and source attribution to describe the current Core assets and limitations.

### Modified files

- `scripts/generate_benchmark_core.py`
- `scripts/validate_benchmark.py`
- `evaluation/benchmark_io.py`
- `evaluation/runners/experiment_runner.py`
- `sera_edit/domain/operations.py`
- `backend/services/score_document_service.py`
- `benchmark/source_scores/*`
- `benchmark/tasks/batch2/*`
- `benchmark/tasks/batch3/*`
- `benchmark/gold_patches/*`
- `benchmark/expected_outputs/*`
- `benchmark/splits/batch2.json`
- `benchmark/splits/batch3.json`
- `benchmark/splits/core.json`
- `benchmark/validation/batch2_report.json`
- `benchmark/validation/core_report.json`
- `benchmark/review/*_human_review.csv`
- `benchmark/README.md`
- `benchmark/BENCHMARK_CARD.md`
- `benchmark/SOURCE_ATTRIBUTION.md`
- `tests/sera_edit/test_extended_operations.py`
- `tests/sera_edit/test_benchmark_io_and_constraints.py`
- `tests/sera_edit/test_benchmark_batch1.py`
- `tests/test_musicxml_dotted_duration_export.py`

### Tests and evidence

- Batch 2 validation: 60 valid, 0 invalid, 60 pending human review.
- Core validation: 120 valid, 0 invalid, 120 pending human review.
- Focused SeraEdit suite after Core generation: 54 passed, 0 failed before adding the Core manifest regression test.
- Extended operations, task resolution, Batch 1, and dotted-duration regression subset: 8 passed, 0 failed.
- No live provider was called and no formal model-performance number was produced.

### Unresolved

- Human review of the 120 task instructions, gold edits, and visual diffs remains pending.
- Weak pickup, arbitrary tuplets, nested/numbered slurs, orchestral multi-part scores, and proprietary host metadata are not represented as supported Core capabilities.
- The formal experiment runner, paired statistics, paper tables/figures, anonymous export, and notation before/after overlay remain incomplete.
- Real MuseScore and Sibelius host compatibility remains unverified.

### Next phase

- Upgrade the experiment runner with configured providers, bounded retry/backoff, rate and concurrency limits, budget enforcement, cache/resume, complete timing/cost capture, and failure serialization; retain mock runs as non-formal plumbing evidence only.

### Paper impact

- Supplies the planned 120-task evaluation substrate and exact category balance, while keeping automated consistency and pending human validation explicitly separate.

## 2026-08-05 - Phase 8: provider adapters and robust experiment runner

### Completed

- Added environment-only OpenAI, DeepSeek, and Qwen OpenAI-compatible provider adapters with configurable endpoint, model, timeout, structured-output support, token usage, request ID, finish reason, and current-price-based estimated cost.
- Added bounded JSON/MusicXML response cleanup permitted by the experimental conditions.
- Replaced instruction-only calls with versioned condition-specific messages: full MusicXML for Condition A, compact target context/schema for Condition B, and target/protected/constraint/fingerprint context for Condition C.
- Added shared response caching, retry/backoff, rate limiting, max concurrency, repetitions, request timeouts, conservative cost reservations, hard budget blocking, task-level resume, Ctrl+C cleanup, and per-task provider failure serialization.
- Added single- and multi-provider configs plus Core/Full entry scripts; formal runs reject mock providers, inline API keys, missing prices, and non-positive budgets.
- Added complete raw request/response evidence, normalized outputs, manifest, config snapshot, JSONL runs, metrics CSV, errors CSV, and summary output.
- Added prompt, config, dependency, Git, and complete benchmark-content hashes; an experiment cannot resume after drift.
- Corrected refusal metrics so a correct refusal is not counted as invalid MusicXML or failed preservation/minimality.
- Diagnosed and corrected two evaluation confounds: exporter-generated 6/8 beams now belong to the canonical notation state and equivalent `B-flat`/`Bb` key spellings no longer count as edits or fingerprint drift.
- Added lazy transaction exports to remove a validation/diff import cycle.

### Modified files

- `sera_edit/generation/prompts.py`
- `sera_edit/generation/response_parser.py`
- `sera_edit/providers/base.py`
- `sera_edit/providers/openai_compatible.py`
- `sera_edit/providers/openai_provider.py`
- `sera_edit/providers/deepseek_provider.py`
- `sera_edit/providers/qwen_provider.py`
- `sera_edit/providers/factory.py`
- `evaluation/conditions/sera_edit_conditions.py`
- `evaluation/metrics/sera_edit_metrics.py`
- `evaluation/runners/runtime_controls.py`
- `evaluation/runners/experiment_runner.py`
- `evaluation/configs/smoke.yaml`
- `evaluation/configs/core_mock.yaml`
- `evaluation/configs/core.example.yaml`
- `evaluation/configs/full.example.yaml`
- `evaluation/configs/providers.example.yaml`
- `evaluation/SERAEDIT_EXPERIMENTS.md`
- `scripts/run_core_experiment.py`
- `scripts/run_full_experiment.py`
- `backend/services/score_document_service.py`
- `sera_edit/execution/transaction.py`
- `sera_edit/execution/diff_engine.py`
- `sera_edit/execution/__init__.py`
- `sera_edit/domain/fingerprints.py`
- `sera_edit/validation/roundtrip_fidelity_validator.py`
- `tests/sera_edit/test_provider_and_runtime_controls.py`
- `tests/sera_edit/test_experiment_conditions.py`
- `tests/sera_edit/test_diff_and_relations.py`
- `tests/sera_edit/test_fingerprints.py`
- `tests/sera_edit/test_roundtrip_fidelity_validator.py`

### Tests and evidence

- Provider/runtime-control and condition tests: 9 passed, 0 failed.
- Beam/fidelity/transaction regression subset: 17 passed, 0 failed.
- Batch 1 after fingerprint regeneration: 30 valid, 0 invalid.
- Core after canonical beam/key regeneration: 120 valid, 0 invalid.
- Core mock v3: 360 completed, 0 runner errors, 0 budget blocks; second run added 0 duplicate rows.
- Core mock v3 now gives preservation/minimality 1.0 for all three conditions, confirming the beam/key metric confounds are removed.
- Core mock v1/v2 remain preserved as diagnostic, non-formal evidence and were not overwritten.
- No live API request was made; all Core mock metrics remain `mock_non_formal` and cannot be reported as provider/model performance.

### Unresolved

- No user-supplied API key, model choice, current price, or cost authorization exists, so no formal live experiment has been run.
- Provider compatibility beyond the documented OpenAI-compatible chat-completion shape remains unverified against live endpoints.
- Automated repair is not yet enabled in the formal Condition C runner.
- Paired statistics, error analysis, tables, figures, anonymous export, and the full paper skeleton remain incomplete.

### Next phase

- Implement deterministic reporting, paired bootstrap/McNemar/Wilcoxon/Holm analysis, error taxonomy outputs, paper tables/figures, and reproducibility verification. Mock-derived assets must remain visibly watermarked as non-formal placeholders.

### Paper impact

- Makes the planned experiment executable and auditable without leaking credentials or allowing stale prompts/benchmarks to contaminate resumed runs; publishable numbers still require an authorized live run.

## 2026-08-05 - Phase 9: bounded repair, statistics, reproducibility, and paper assets

### Completed

- Added Condition C-only bounded repair: deterministic schema cleanup first, then at most two provider repair attempts carrying the instruction, invalid patch, validation errors, allowed scope, protected scope, and strict response schema.
- Preserved the experimental boundary: Condition B performs no repair and Condition A receives no ScorePatch/protected-scope advantage.
- Aggregated provider calls, latency, tokens, estimated cost, repair trace, repair success, and repair-added cost into auditable raw and normalized outputs.
- Added paired descriptive/bootstrap analysis, exact McNemar tests, Wilcoxon signed-rank tests, rank-biserial effects, Holm correction, refusal metrics, and category breakdowns; condition order now follows the experiment manifest.
- Added deterministic paper tables, five non-decorative figures in PNG/SVG/PDF where supported, captions, error taxonomy output, and a real event-level edit case figure.
- Added metric recomputation, full reproducibility verification, and secret-scanned anonymous ZIP export commands.
- Added conference-neutral Markdown/LaTeX short-paper sources, bibliography, related-work notes, supplementary guide, submission notes, and reproducibility checklist. Formal result slots remain explicit placeholders.
- Executed `core_mock_120_v5`: 120 tasks × 3 conditions = 360 completed rows, 0 runner errors; repeat execution created 0 duplicate rows. The run is permanently marked `mock_non_formal`.

### Main files

- `sera_edit/generation/prompts.py`
- `evaluation/conditions/sera_edit_conditions.py`
- `evaluation/metrics/sera_edit_metrics.py`
- `evaluation/runners/experiment_runner.py`
- `evaluation/statistics/paired_analysis.py`
- `evaluation/reporting/paper_assets.py`
- `scripts/recompute_metrics.py`
- `scripts/verify_reproducibility.py`
- `scripts/generate_paper_assets.py`
- `scripts/export_anonymous_package.py`
- `paper/manuscript/seraedit_icmc_short_paper.md`
- `paper/manuscript/seraedit_icmc_short_paper.tex`
- `paper/manuscript/references.bib`
- `paper/supplementary/REPRODUCIBILITY_CHECKLIST.md`
- `tests/sera_edit/test_statistics.py`

### Tests and evidence

- Repair-focused backend subset: 16 passed, 0 failed.
- Core mock v5: 360/360 completed, 0 errors, resume added 0 rows.
- Recomputed `metrics_recomputed.csv` exactly matched the original 360-row `metrics.csv`.
- Reproducibility verification passed config, benchmark, prompt, dependency, evidence-file, metric-equality, and expected-run-count checks.
- Core benchmark revalidation: 120 valid, 0 invalid, 120 pending human review.
- SeraEdit suite during final verification: 70 passed, 0 failed.
- Anonymous package: 1,099 files, no detected secret, raw provider outputs excluded; mock classification retained.

### Unresolved

- No authorized live provider/model run exists, so mock tables, figures, statistics, latency, and cost values are pipeline fixtures only and cannot be cited as model performance.
- All 120 benchmark tasks still require documented human music review before a formal study.
- Tectonic was detected but could not download its format bundle because of a TLS handshake failure; TeX Live/MacTeX is absent, so the `.tex` source has not produced a PDF in this environment.
- Mermaid architecture sources are retained, but static Mermaid export was blocked by unavailable CLI/network rendering; Matplotlib paper figures were generated successfully.

### Paper impact

- The full analysis and manuscript asset chain is now reproducible from saved outputs without manual number copying, while non-formal evidence is prevented from becoming a paper claim.

## 2026-08-05 - Phase 10: authoritative before/after UI and packaged Electron hardening

### Completed

- Added an authoritative event-level comparison directly below the score canvas, showing current ScoreDocument versus the uncommitted transaction clone, target/protected classification, C4→D4-style field changes, fingerprints, and protected-scope change count.
- Normalized validation warnings in `ScoreCanvas` so strict issue objects no longer cause the runtime `e.match is not a function` crash.
- Allowed warning-only proposals with zero validation errors to be applied; invalid and unsupported proposals remain blocked.
- Corrected sparse-score MusicXML round-trip validation: transactions compare re-imports against the deterministic export-domain ScoreDocument, and complete rest-only measures are valid MusicXML content warnings rather than empty-measure errors.
- Published the serving backend PID in the runtime file and desktop status endpoint; Electron can safely adopt a verified existing desktop backend and terminates the full PyInstaller process tree on exit.
- Replaced the unavailable PATH-relative `taskkill.exe` call with the System32 absolute executable plus checked fallback.
- Updated the packaged smoke script for Electron's actual user-data path, graceful window shutdown, runtime-file removal, and orphan-backend assertions.
- Split packaging commands so the default `npm run dist` and complete Windows build produce the stable unpacked application; the optional portable target is now explicit and cannot block the primary deliverable.
- Rebuilt the PyInstaller backend and Electron `win-unpacked` local application.

### Main files

- `frontend/src/workbench/StrictScoreComparison.tsx`
- `frontend/src/workbench/SeraEditResearchPanel.tsx`
- `frontend/src/workbench/ScoreCanvas.tsx`
- `frontend/src/workbench/ScoreWorkbench.tsx`
- `frontend/src/styles.css`
- `sera_edit/execution/transaction.py`
- `backend/validation/musicxml_validator.py`
- `backend/services/desktop_session_broker.py`
- `packaging/backend/run_backend_packaged.py`
- `electron/main.js`
- `packaging/windows/smoke_test_packaged_app.ps1`
- related backend, frontend, lifecycle, and packaging regression tests

### Tests and visible evidence

- Complete backend suite: 267 passed, 0 failed.
- Frontend suite: 99 passed, 0 failed across 69 files; production build passed with the existing large-chunk warning.
- Lifecycle/package contract subset: 24 passed, 0 failed before the complete suites.
- Packaged smoke passed for staged backend at port 8000, legacy local launcher at port 8100, and Electron desktop at port 8000.
- Complete `build_windows_app.ps1` finished successfully in 407.5 seconds and wrote a fresh manifest with `electron_packaged=true`, a non-empty unpacked executable path, and no build error.
- After packaged shutdown: 0 project Sera/SeraBackend processes, 0 listeners on ports 8000/8100, and no Electron runtime port file.
- Visible Electron smoke, without an external browser, showed current `C4` versus proposed `D4`, changed=1, added=0, deleted=0, protected unexpected changes=0, warning-only validation, enabled Apply, successful Apply, enabled Undo, successful Undo, and enabled Redo.

### Unresolved

- The optional `npm run dist:portable` target remains unverified after the earlier combined build hung; the tested primary deliverable is `dist_desktop/release/win-unpacked/Sera.exe`.
- The local rule generator remains intentionally narrow and is not formal LLM evidence.
- MuseScore QML artifact and versioned MusicXML exchange exist, but real MuseScore and Sibelius host round trips remain unverified.
- Human benchmark review, formal live provider runs, LaTeX PDF compilation, and static Mermaid export remain external completion gates.

### Paper impact

- The demo now exposes the central reliability claim directly: an authoritative source state, bounded proposed state, protected-region evidence, and explicit apply/undo transaction boundary in a tested local desktop application.

## 2026-08-05 - Phase 11: backend-ready desktop startup

### Completed

- Replaced the packaged Electron shell's 15-second runtime-file-only startup gate with an actual `/health` readiness check.
- Added an environment-overridable startup timeout with safe defaults of 90 seconds when packaged and 45 seconds in development.
- Added an inline Chinese startup page before the Workbench is loaded, including first-launch guidance and a progress state; terminal startup errors now remain inside the application window instead of appearing as a transient modal dialog.
- Extended the frontend's secondary backend gate from 5 seconds to 30 seconds and updated the user-visible health-check wording.
- Extended the packaged smoke readiness budget to 120 seconds so a cold PyInstaller extraction is not misclassified as a failure.
- Rebuilt the frontend bundle and Electron `win-unpacked` desktop application.

### Main files

- `electron/main.js`
- `frontend/src/desktop/backendHealth.ts`
- `frontend/src/desktop/startupScreen.tsx`
- `tests/test_desktop_launcher.py`
- `packaging/windows/smoke_test_packaged_app.ps1`
- `README.md`

### Tests and visible evidence

- Desktop launcher and packaging subset: 16 passed, 0 failed.
- Complete frontend suite: 99 passed, 0 failed across 69 files; production build passed with the existing large-chunk warning.
- Fresh Electron directory build completed successfully in 47.9 seconds.
- Visible cold launch produced exactly one Sera window, no error dialog, reached the Workbench in approximately 12 seconds on this machine, and returned `status: ok` from the published backend `/health` endpoint.
- Packaged smoke passed the staged backend at port 8000, compatibility launcher at port 8100, and Electron desktop at port 8000 in 40.6 seconds.

### Unresolved

- Startup time depends on Windows disk and security-scanner performance; the first-run loading page and timeout path are contract-tested, while this machine's backend became healthy quickly enough that the loading page was only briefly visible.
- The optional portable single-file target remains unverified; the tested deliverable is `dist_desktop/release/win-unpacked/Sera.exe`.

### Paper impact

- The local demo now exposes backend readiness as an explicit state and no longer presents a recoverable cold start as an application failure.

## 2026-08-05 - Phase 12: host-first Agent Console product boundary

### Completed

- Replaced the default Workbench surface with `SeraAgentConsole`, organized around host connection, Agent conversation, and validated proposal review.
- Removed the built-in score canvas, note-entry controls, playback strip, Score Inspector, manual notation properties, and editor operation history from the default product path.
- Kept the existing strict patch generator, schema/structural/protected-scope validation, transactional apply, revision export, and non-destructive undo-as-revision behavior.
- Made the host-provided measure/staff/voice selection authoritative; the fallback import path exists only to create a host-style MusicXML bridge session.
- Kept legacy generation and Workbench code behind `VITE_SERA_ENABLE_LEGACY_GENERATION=true` for internal compatibility only.
- Added focused React tests asserting both the reduced product surface and the host-session → validated patch → exported revision flow.
- Rebuilt the frontend bundle and Electron `win-unpacked` desktop application.

### Main files

- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/agent/__tests__/SeraAgentConsole.test.tsx`
- `frontend/src/App.jsx`
- `frontend/src/styles.css`
- `README.md`

### Tests and evidence

- Focused Agent Console tests: 2 passed, 0 failed.
- Complete frontend suite: 101 passed, 0 failed across 70 files.
- Frontend production build: 213 modules transformed; build completed successfully.
- Electron directory packaging completed successfully with the new Agent Console assets.
- Packaged smoke passed for the staged backend, compatibility launcher, and Electron desktop runtime.
- Bridge/desktop/API/packaging regression subset: 20 passed, 0 failed.
- Visible packaged Electron inspection showed only the host connection rail, Agent conversation, and proposal review; no score canvas, note-entry palette, playback, Inspector, or manual editing controls were present.
- A local MuseScore-shaped bridge session was delivered through the real desktop broker and displayed `Agent QA`, host `MuseScore Studio`, and selection `M1–M1`. This validates the local bridge/UI handoff, not a real MuseScore installation.

### Unresolved

- Real MuseScore QML and Sibelius host round trips remain unverified on installed host applications.
- The current MuseScore delivery contract opens a reviewed MusicXML revision in a new host tab; in-place host patching is not claimed.
- Official MuseScore/Sibelius brand assets are not bundled; the console uses neutral text/monogram host marks.

### Paper impact

- The demo now matches the research claim more closely: Sera is a reliable language-guided editing and validation layer above a professional notation host, not a replacement notation editor.

## 2026-08-05 - Phase 13: MuseScore 4.5.2 bridge compatibility recovery

### Completed

- Diagnosed the real plug-in failure on MuseScore Studio 4.5.2 build 251141402. The MuseScore log records `PluginAPI::writeScore | Not implemented!!`; the temporary directory was writable, so this was an unavailable host API rather than a Sera startup delay or filesystem problem.
- Replaced the QML `writeScore`/`readScore` dependency with a saved-file picker plus local MuseScore CLI conversion. Native/compressed `.mscz`, `.mscx`, and `.mxl` sources are converted to temporary MusicXML; `.musicxml` and `.xml` are read directly.
- Preserved the live MuseScore measure/tick/staff selection context and desktop broker handoff while keeping the source score non-destructive.
- Added a backend endpoint that opens an accepted MusicXML revision through MuseScore CLI as a new score, without claiming in-place modification.
- Added robust MuseScore executable discovery for PATH, standard program directories, `MUSESCORE_PATH`, and drive-root installations such as `D:\MuseScore 4\bin\MuseScore4.exe`.
- Updated and reinstalled Sera Score Bridge v0.3.0. The previous installed plug-in was backed up before replacement.

### Main files

- `backend/services/musescore_file_bridge_service.py`
- `backend/integrations/notation_hosts.py`
- `backend/services/notation_bridge_service.py`
- `backend/app.py`
- `integrations/musescore/SeraBridge/SeraBridge.qml`
- `integrations/musescore/README.md`
- `scripts/install_musescore_bridge.ps1`
- `tests/test_musescore_file_bridge_service.py`
- `tests/test_musescore_qml_bridge_contract.py`
- `tests/test_notation_bridge_service.py`

### Tests and real host evidence

- Focused bridge, QML contract, notation-session, and desktop broker suite: 12 passed, 0 failed.
- Direct real CLI conversion of `D:\Desktop\2026\121.mxl` completed with return code 0 in about 1.1 seconds and produced 61,241 bytes of MusicXML.
- Full Windows packaged build completed successfully; the packaged staged-backend, compatibility-backend, and Electron smoke test passed.
- Real MuseScore 4.5.2 plug-in test created session `bridge_20260805_123611_5ced16d4`. Sera Desktop was brought forward and displayed host `MuseScore Studio`, the imported score, and selection `M1–M1` without opening an external browser.
- A subsequent edit request was rejected by strict protected-scope validation. That is the intended safety behavior of the edit pipeline and is independent of the now-working transport bridge.

### Unresolved

- MuseScore 4.5.2 cannot expose unsaved in-memory edits through the tested QML API; users must press `Ctrl+S` before sending.
- In-place editing of the currently open MuseScore score and single-step MuseScore Undo are not implemented or claimed.
- Opening the reviewed revision is covered by backend/API contract tests but was not completed as a visible real-host action in this run because the tested proposal was correctly rejected before revision creation.
- Sibelius host automation remains unimplemented.

### Paper impact

- The demonstration now has real-host evidence for the MuseScore-to-Sera input path and documents the exact compatibility fallback instead of treating the host bridge as an unverified artifact.

## 2026-08-05 - Phase 14: host-beam preservation and protected-scope false-positive fix

### Completed

- Reproduced the real `121.mxl` failure: a 16-note measure-1 transpose was reported as 50 changed events because the transaction recomputed beam metadata over the entire score.
- Confirmed that 34 `E11` errors came from out-of-target `beam` changes in later measures, not from pitch edits outside the selected measure.
- Added source-aware beam materialization. MusicXML imported from MuseScore, other notation bridges, or generic import now preserves both explicit host beams and intentional beam absence; Sera-owned generated scores retain deterministic automatic beaming.
- Made transaction diff, protected-scope validation, and semantic postconditions compare the same beam-materialized before/after baseline.
- Kept round-trip beam fidelity validation active, rather than globally ignoring the `beam` field.
- Added regression coverage for custom host beaming outside the target scope and for generated-score beam derivation outside the target scope.

### Main files

- `backend/notation/beaming.py`
- `backend/services/score_document_service.py`
- `sera_edit/execution/transaction.py`
- `tests/sera_edit/test_transaction.py`
- `integrations/musescore/README.md`

### Tests and real-score evidence

- SeraEdit, MusicXML/beaming, notation bridge, MuseScore bridge, and desktop broker regression set: 95 passed, 0 failed.
- Source-runtime replay against live session `bridge_20260805_131953_2c664840` and `D:\Desktop\2026\121.mxl` returned 16 changed elements, all with field `pitch`.
- Protected-scope replay returned 0 unexpected changes across 150 protected elements and preservation rate 1.0.
- MusicXML round-trip fidelity remained valid; the proposal had no validation errors and was available for application.
- Rebuilt the Windows `win-unpacked` application successfully; packaged backend, compatibility launcher, and Electron desktop smoke all passed.
- Packaged-backend replay created session `bridge_20260805_133756_2c0aee06` from the real `121.mxl` through MuseScore CLI and independently confirmed 16 pitch-only changes, 0 validation errors, 0 protected changes, preservation rate 1.0, valid round-trip fidelity, and an available proposal.

### Unresolved

- The current local natural-language generator still supports only the documented bounded instruction subset.
- Rhythm-changing operations on complex cross-staff beaming need dedicated target-lane rebeaming before being promoted as a fully host-faithful feature.
- Real visible opening of an accepted revision in MuseScore remains to be completed after a valid proposal is applied.

### Paper impact

- Non-target preservation metrics no longer count deterministic exporter beaming as an agent edit, while host-authored beaming remains part of round-trip fidelity checks.

## 2026-08-05 - Phase 15: source-preserving MuseScore revision export

### Completed

- Reproduced the malformed visible revision from `D:\Desktop\2026\121.mxl`: the old full-score rebuild expanded 171 source notes to 199 notes, expanded 36 rests to 64 rests, attached `mf` to all 199 note events, and removed MuseScore `defaults`, `print`, page-layout, and system-layout data.
- Traced the failure to `NotationBridgeService.export_revision()`: it exported the reduced canonical `ScoreDocument` as a brand-new MusicXML document. Imported effective dynamics and normalized implicit rests were therefore materialized as explicit notation, while host-only engraving metadata was lost.
- Replaced that fallback with a source-preserving MusicXML patcher. It starts from the current host artifact and patches only supported target nodes; unsupported structural changes fail closed instead of silently rebuilding the whole score.
- Added source-preserving support for pitch, articulation, dynamic, title, and composer edits. Dynamic changes are emitted as measure/staff directions rather than duplicated onto every note.
- Added revision metadata and API evidence for export mode, changed event count, changed fields, and source-preservation checks.
- Updated MuseScore Bridge to v0.3.1 with clearer separate-window behavior, duplicate-open protection, and a useful no-response/startup error instead of a misleading JSON parse message.

### Main files

- `backend/services/musicxml_source_patch_service.py`
- `backend/services/notation_bridge_service.py`
- `integrations/musescore/SeraBridge/SeraBridge.qml`
- `integrations/musescore/README.md`
- `tests/test_musicxml_source_patch_service.py`
- `tests/test_notation_bridge_service.py`
- `tests/test_musescore_qml_bridge_contract.py`
- `scripts/verify_source_preserving_revision.ps1`

### Tests and real-score evidence

- Focused source-patcher, notation-bridge, transaction, API, and MuseScore bridge suite: 24 passed, 0 failed.
- Broader SeraEdit/MusicXML/bridge regression suite: 98 passed, 0 failed.
- Real-source replay on `121.mxl` changed exactly 16 target pitches and reported `export_mode: source_preserving_patch`.
- Source and revision both contain 171 notes, 36 rests, 0 note-level dynamics, 1 `defaults` block, 1 page-layout block, 4 `print` elements, and 4 system-layout blocks.
- All eight non-target measures were byte-equivalent after XML normalization; strict patch validation returned no blocking errors.
- The packaged-backend replay created session `bridge_20260805_140528_f9d35db0` and independently reproduced the same 16 pitch-only changes and source-preservation counts.
- The legacy MusicXML completeness checker reported six incomplete-duration findings on both the unedited source and the revision. Their lists were identical, so the revision introduced no new MusicXML validation issue; the source-preserving path also did not materialize the validator's canonical rest suggestions.
- Windows `win-unpacked` rebuilt successfully, and packaged staged-backend, compatibility-launcher, and Electron smoke checks all passed.

### Unresolved

- Existing malformed revisions created by the old exporter are not repairable in place; a new bridge session must be created from the original saved score.
- Structural operations such as insertion, deletion, duration changes, and meter changes are intentionally rejected by source-preserving export until host-faithful XML patch implementations are added.
- Cross-part, cross-staff, and relation-heavy edits need dedicated source mapping tests before they can be claimed as host-faithful.

### Paper impact

- The host integration now preserves the original engraving source outside explicitly patched XML nodes, so visible layout damage and duplicated effective dynamics are no longer hidden behind successful canonical validation.

## 2026-08-05 - Phase 16: live LLM API control for the host-first Agent Console

### Completed

- Replaced the Agent Console's local-rule-only generation path with an auto-selecting live/local runtime path.
- Added an OpenAI Responses API adapter using strict JSON Schema output, `store: false` by default, bounded output tokens, configurable reasoning effort, token/latency/request evidence, sanitized failures, and environment-only credentials.
- Preserved the existing Chat Completions adapters for DeepSeek, Qwen, and custom OpenAI-compatible endpoints without changing formal experiment condition code.
- Added a smaller transport schema for model planning. The model may only propose transpose, exact pitch, dynamic, and bounded articulation operations; the server owns source fingerprint, scopes, operation IDs, expected effects, provenance, and final ScorePatch construction.
- Restricted model-selected event IDs to note events already inside the authoritative host target scope. Hallucinated or out-of-scope IDs are rejected before transaction preview.
- Kept explicit model refusals authoritative and added visible local-rule fallback for missing credentials, timeouts, network/provider errors, or invalid model output.
- Added `GET /sera-edit/provider-status`, with provider/model/transport/config state but no credential value.
- Added per-user packaged configuration at `%LOCALAPPDATA%\Sera\llm.env` and an interactive hidden-key PowerShell setup script.
- Added Agent Console provider state and per-proposal provider/model/latency/fallback evidence.

### Main files

- `sera_edit/providers/openai_responses.py`
- `sera_edit/providers/runtime.py`
- `sera_edit/generation/llm_patch_generator.py`
- `sera_edit/api/routes.py`
- `backend/app.py`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/api.js`
- `frontend/src/score/scoreTypes.ts`
- `scripts/configure_llm.ps1`
- `docs/LLM_API_SETUP.md`
- `tests/sera_edit/test_live_patch_generator.py`
- `tests/sera_edit/test_provider_and_runtime_controls.py`
- `tests/sera_edit/test_api_routes.py`

### Tests and evidence

- Initial LLM provider, strict generator, route, credential safety, and transaction subset: 17 passed, 0 failed.
- Agent Console focused tests: 2 passed, 0 failed.
- Full SeraEdit/MusicXML/notation-bridge regression selection: 105 passed, 0 failed.
- Full frontend test run: 70 test files and 101 tests passed, 0 failed.
- Frontend production build completed successfully with 213 transformed modules.
- `configure_llm.ps1` passed Windows PowerShell parser validation.
- A fake Responses API payload passed through the real `/sera-edit/generate-preview` route, produced a source-bound ScorePatch, passed full dry-run validation, and returned no test credential material.
- Windows `1.0.0-dev.3` unpacked application rebuilt successfully. Packaged staged backend, compatibility launcher, and Electron desktop smoke checks all passed.
- Packaged-backend replay against `D:\Desktop\2026\121.mxl` reported `local_rule` when no credential was configured, exposed no credential field, changed exactly 16 target pitches, retained all note/rest/dynamic/layout counts, and kept all eight non-target measures equivalent.
- The replay preserved the source score's pre-existing duration-validation findings unchanged; it introduced no new validation error.

### Unresolved

- No real paid-provider request was executed because no user API credential was supplied for this implementation run. Live network/model behavior remains pending user-key verification.
- LLM planning is intentionally limited to operations already covered by source-preserving MusicXML export. Structural editing remains fail-closed.
- Provider prices are intentionally unset and must be configured from current provider pricing before formal cost reporting.

### Paper impact

- The demo can now compare local deterministic parsing with a real model-backed structured planner while preserving identical validation, protected-scope, transaction, and host-export safety layers.

## 2026-08-05 - Phase 17: in-app encrypted LLM provider configuration

### Completed

- Added a first-class “模型设置” dialog to the Sera Agent Console. Users can configure OpenAI, DeepSeek, Qwen, or a custom OpenAI-compatible endpoint without leaving the desktop application.
- Added provider-specific model and base-URL defaults, a password-only API Key field, reasoning-effort selection, local fallback control, visible save errors, and immediate provider-state refresh.
- Added local provider configuration `PUT` and `DELETE` endpoints. Neither endpoint echoes credential values; status continues to expose only boolean/configuration evidence.
- Added Windows DPAPI credential protection. In-app API Keys are encrypted for the current Windows user before the per-user file is written; no plaintext credential is persisted by the in-app path.
- Kept the previous PowerShell configuration path as a compatibility route. Re-saving an existing same-provider environment credential through the UI migrates it to DPAPI-protected storage.
- Added atomic configuration writes, remote HTTPS enforcement, localhost-only HTTP allowance, single-line/length validation, and immediate in-process activation without an application restart.
- Added a reusable packaged-runtime verification script that saves a dummy credential, proves plaintext absence, clears the credential, and validates the frozen backend's DPAPI support.
- Bumped the packaged desktop and backend version to `1.0.0-dev.4`.

### Main files

- `sera_edit/providers/credential_protection.py`
- `sera_edit/providers/runtime.py`
- `sera_edit/api/routes.py`
- `frontend/src/agent/LLMProviderSettingsDialog.tsx`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/api.js`
- `frontend/src/styles.css`
- `packaging/windows/restage_frontend.ps1`
- `scripts/verify_packaged_llm_configuration.ps1`
- `docs/LLM_API_SETUP.md`

### Tests and evidence

- SeraEdit/MusicXML/notation-bridge regression selection: 109 passed, 0 failed.
- Frontend suite: 70 test files and 103 tests passed, 0 failed.
- Frontend production build passed with 214 transformed modules.
- Native Windows DPAPI encrypt/decrypt round-trip passed.
- Rendered UI QA passed at the normal desktop viewport and a 600 x 800 responsive viewport. The settings dialog opened, provider changes updated model/base URL, the API Key field remained a password input, and no relevant browser console warning or error was present.
- Windows `1.0.0-dev.4` unpacked application rebuilt successfully. Packaged staged backend, compatibility launcher, and Electron desktop smoke checks all passed.
- Frozen-backend credential replay returned `credential_storage: windows_dpapi`, `plaintext_on_disk: false`, and removed the encrypted value when returning to local rules.
- Packaged real-score replay against `D:\Desktop\2026\121.mxl` still changed exactly 16 target pitches, preserved all notation/layout counts, and kept all eight non-target measures equivalent.

### Unresolved

- A real paid-provider request still requires the user to enter their own credential in Sera; no credential was invented or embedded during development.
- DPAPI-bound credentials cannot be moved to another Windows user or computer; the key must be entered again there.
- Structural score edits remain fail-closed until the source-preserving MusicXML patcher supports them.

### Paper impact

- The live-model demo can now be configured entirely inside the desktop application without weakening the structured-patch or credential-safety boundaries.

## 2026-08-06 - Phase 18: separated conversation and repairable safe proposals

### Completed

- Split ordinary LLM conversation from score-edit proposal generation. `/sera-edit/chat` returns plain text through a code path with no ScorePatch, transaction, apply, or export action.
- Added separate “对话” and “修改提案” modes in the Agent Console. Conversation remains available without a host; proposal generation still requires a connected host score and selection.
- Diagnosed the real configured DeepSeek failure: the provider returned one operation as an object while the server correctly required an operations array.
- Strengthened the proposal prompt with an exact single-operation array example and an explicit array invariant.
- Added deterministic repair for an unambiguous single-operation-object shape plus at most one bounded LLM format-repair request. Scope, event-ID whitelist, protected scope, and operation whitelist remain server-owned and fail closed.
- Added visible proposal evidence for repair strategy and request count.
- Bumped the packaged desktop and backend version to `1.0.0-dev.5`.

### Main files

- `sera_edit/generation/conversation_agent.py`
- `sera_edit/generation/llm_patch_generator.py`
- `sera_edit/api/routes.py`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/api.js`
- `frontend/src/score/scoreTypes.ts`
- `frontend/src/styles.css`
- `tests/sera_edit/test_live_patch_generator.py`
- `tests/sera_edit/test_api_routes.py`
- `frontend/src/agent/__tests__/SeraAgentConsole.test.tsx`
- `docs/LLM_API_SETUP.md`

### Tests and evidence

- Targeted strict generator and API route tests: 14 passed, 0 failed.
- Full `tests/sera_edit` suite: 86 passed, 0 failed.
- Notation bridge, MuseScore file/QML bridge, source-preserving MusicXML patch, and desktop session regressions: 15 passed, 0 failed.
- Full frontend suite: 70 test files and 104 tests passed, 0 failed.
- Frontend production build passed with 214 transformed modules.
- A real configured DeepSeek call returned a live, source-bound transpose proposal in one request with no local fallback and no repair attempt.
- A separate real DeepSeek conversation call answered “2个半音”; the response contained no patch field.
- Windows `1.0.0-dev.5` unpacked application rebuilt successfully. Packaged staged backend, compatibility launcher, and Electron desktop smoke checks all passed.
- The frozen packaged backend reported `1.0.0-dev.5`; its real DeepSeek chat route returned plain text with no patch field, and its real proposal route returned a live one-request patch with `valid` dry-run validation and no local fallback.

### Unresolved

- Live-model proposal planning remains intentionally limited to transpose, exact pitch, dynamics, and three articulations until additional MusicXML-preserving operations pass host regression tests.
- Provider behavior may change with model revisions; malformed, out-of-scope, or unsupported responses continue to fail closed.

### Paper impact

- The demo now distinguishes conversational assistance from experimentally relevant structured patch generation, and records bounded repair evidence without weakening protected-scope validation.

## 2026-08-06 - Phase 19: theory-guided, host-preserving Composer V0.1

### Completed

- Added an independent `sera_edit/composer` namespace for typed CompositionPlan generation, traceable theory retrieval, deterministic candidate realization, musical critics, ranking, and runtime-provider integration.
- Restricted the first executable composer baseline to pitch recomposition over an existing 1–8 measure host scaffold. Rhythm, event count, instrumentation, layout, source fingerprint, target scope, and protected scope remain immutable.
- Limited the LLM to high-level choices: mode, style, Roman-numeral harmony, texture, motif strategy, tension, dynamics, and orchestration notes. The server owns score facts, event IDs, exact pitches, allowed operations, and all safety decisions.
- Added three modes: theory variation, melody-preserving reharmonization, and plan-only orchestration advice. Structural orchestration remains fail-closed because the source-preserving bridge does not yet support instrument/part mutations.
- Added multi-candidate deterministic realization and independent critics for transaction validity, chord-tone anchoring, cadence, register, large leaps, voice crossing, and style-aware voice leading.
- Added `/sera-edit/composer/preview`; it returns plans, theory trace, ranked candidates, preview transactions, and explicit baseline guarantees without committing score state.
- Added a third Agent Console mode, “创作草案”. Candidate selection feeds the existing ScorePatch review/apply/export path instead of bypassing it.
- Added product/research documentation and the Mermaid source for the Composer architecture.
- Added repository-wide test isolation so a user's configured live provider cannot be consumed by deterministic legacy tests; tests that exercise providers continue to opt in explicitly with fake credentials/providers.
- Bumped packaged desktop and backend version to `1.0.0-dev.6`.

### Main files

- `sera_edit/composer/models.py`
- `sera_edit/composer/theory_knowledge.py`
- `sera_edit/composer/planner.py`
- `sera_edit/composer/candidate_generator.py`
- `sera_edit/composer/critics.py`
- `sera_edit/composer/pipeline.py`
- `sera_edit/api/routes.py`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/score/scoreTypes.ts`
- `frontend/src/api.js`
- `frontend/src/styles.css`
- `tests/sera_edit/test_composer_pipeline.py`
- `frontend/src/agent/__tests__/SeraAgentConsole.test.tsx`
- `docs/SERA_COMPOSER_V01.md`
- `docs/architecture/sera_composer_v01.mmd`

### Tests and evidence

- Targeted Composer backend tests: 7 passed, 0 failed.
- Targeted Agent Console tests including the create-select-review handoff: 6 passed, 0 failed.
- Full Python regression suite: 298 passed, 0 failed. The dedicated `tests/sera_edit` suite contributed 93 passing tests.
- Full frontend suite: 70 test files and 105 tests passed, 0 failed.
- Frontend production build passed with 214 transformed modules.
- A real configured DeepSeek request produced three ranked Composer candidates; every candidate had a valid preview transaction and a valid final review, and every baseline guarantee remained true.
- Rendered browser QA imported a host MusicXML file, generated three reviewed candidates, exposed theory/safety/playability scores and trace IDs, and handed the selected candidate into the existing valid ScorePatch review without applying it. Conversation and ordinary edit tabs remained present; no relevant browser console warning or error was recorded. The same state remained accessible at the normal desktop viewport and at 720 x 900.
- Real host-source replay used `D:\Desktop\2026\121.mxl` through MuseScore CLI conversion. The selected Composer patch changed 108 target pitches, changed no rhythm or structural field, re-imported successfully, and preserved measure, note, part, staff-layout, page-layout, system-layout, appearance, print, credit, direction, and harmony counts exactly. Export mode was `source_preserving_patch`.
- The Mermaid source rendered successfully to SVG and PNG and was visually inspected at original resolution without cutoff or overlap.
- Windows `1.0.0-dev.6` unpacked application rebuilt successfully. Staged backend, compatibility launcher, and Electron desktop smoke checks all passed; the frozen Composer endpoint returned two valid reviewed candidates.

### Unresolved

- Structural composition and direct orchestration edits remain fail-closed until the source-preserving MusicXML bridge and host undo contract support part/instrument/event mutations.
- Deterministic theory scores are ranking proxies, not universal aesthetic-quality judgments; formal claims require blind human evaluation.
- The curated theory store currently contains original engineering summaries rather than a licensed source corpus.

### Paper impact

- The new experimental factor is no longer merely “LLM versus rules”. It can compare one-shot editing with a traceable hierarchy: theory retrieval, typed planning, deterministic multi-candidate realization, independent criticism, and the same protected ScorePatch transaction boundary.

## 2026-08-06 - Phase 20: responsive Composer progress and bounded live planning

### Completed

- Diagnosed the reported “生成创作候选没有动静” symptom against the running packaged desktop. The control was firing correctly, but the configured provider allowed a 90-second synchronous wait and the only status text lived at the bottom of the proposal rail. A real earlier DeepSeek plan took about 40 seconds, making the interaction appear inert.
- Added a Composer-specific 30-second live-planner ceiling, bounded to 5–60 seconds through `SERA_COMPOSER_LLM_TIMEOUT_SECONDS`. Provider timeout now falls back to the deterministic theory plan instead of leaving the user waiting for the global 90-second limit.
- Added `planner_mode: auto|local` to the preview contract. `local` provides an explicit deterministic path while preserving the same candidate critics and ScorePatch transaction boundary.
- Added an immediate visible progress card with spinner, elapsed seconds, stage text, progress bar, fallback explanation, and `aria-live` status semantics.
- Added a 45-second frontend safety timeout and a visible error card. Transport failure no longer collapses back to the misleading “等待编辑指令” empty state.
- Bumped the backend and Windows desktop package to `1.0.0-dev.7`.

### Main files

- `sera_edit/composer/pipeline.py`
- `sera_edit/api/routes.py`
- `frontend/src/api.js`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/styles.css`
- `tests/sera_edit/test_composer_pipeline.py`
- `frontend/src/agent/__tests__/SeraAgentConsole.test.tsx`

### Tests and evidence

- Targeted Composer backend tests: 9 passed, 0 failed.
- Targeted Agent Console tests: 7 passed, 0 failed.
- Full Python regression suite: 300 passed, 0 failed.
- Full frontend suite: 70 test files and 106 tests passed, 0 failed.
- Frontend production build passed with 214 transformed modules.
- Browser interaction QA imported a host MusicXML file and clicked “生成创作候选”. The UI showed the progress card at 0 seconds, advanced its stage text and timer, and then displayed three valid candidates. Browser console warnings/errors: 0. The candidate controls remained accessible at the normal desktop viewport and 720 x 900.
- Windows `1.0.0-dev.7` rebuilt successfully. Staged backend, compatibility launcher, and Electron desktop smoke checks passed.
- Frozen backend replay reported version `1.0.0-dev.7`; `planner_mode=local` returned two candidates with `deterministic_theory` evidence and a 30-second planner ceiling.

### Unresolved

- A slow provider may still use the entire 30-second budget before deterministic fallback. This is intentional and now visible; users who require immediate offline behavior can select local rules in the in-app model settings.
- Provider requests are synchronous inside the backend worker. Streaming partial CompositionPlan tokens is outside this fix and is not required for safe candidate generation.

### Paper impact

- Planner latency and fallback are now explicit experimental evidence instead of hidden UI delay, improving reproducibility of live-versus-deterministic Composer comparisons.

## 2026-08-21 - Phase 21: compliant automatic routing for melody rewrite proposals

### Completed

- Reproduced the reported provider refusal: the ordinary strict proposal prompt was instructed to reject new melodic material even though the separate Composer pipeline could safely realize it over existing events.
- Added a conservative deterministic intent router for explicit melody/theme/motif rewrite or variation and reharmonization instructions in Chinese and English. Atomic edits remain in the strict patch generator; vague aesthetic requests remain unsupported.
- Routed explicit compositional edits from `/sera-edit/generate-preview` into the existing Composer planner, three-candidate realization, independent critics, protected-scope validation, and transaction preview.
- Compiled only the best valid candidate back into the ordinary proposal channel. The returned patch contains source-bound `set_pitch` operations over existing event IDs; rhythm, event count, instrumentation, layout, target scope, and protected scope remain unchanged.
- Added `composition_evidence` and generator evidence for route, candidate count, selected candidate, score, theory plan, selected review, and baseline guarantees.
- Updated the proposal UI to display “Composer 自动路由”, reviewed candidate count, and best score instead of presenting the route as a format repair or an unsupported instruction.
- Bumped backend and Windows desktop version to `1.0.0-dev.8`.

### Main files

- `sera_edit/composer/intent_router.py`
- `sera_edit/generation/llm_patch_generator.py`
- `frontend/src/score/scoreTypes.ts`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `tests/sera_edit/test_composer_intent_router.py`
- `tests/sera_edit/test_api_routes.py`
- `frontend/src/agent/__tests__/SeraAgentConsole.test.tsx`

### Tests and evidence

- Intent-router, API-route, and live-patch targeted backend selection: 24 passed, 0 failed.
- Targeted Agent Console suite: 8 passed, 0 failed.
- Full Python regression suite: 310 passed, 0 failed.
- Full frontend suite: 70 test files and 107 tests passed, 0 failed.
- Frontend production build passed with 214 transformed modules.
- Source API replay of “重写当前选区的旋律” returned `generated`, `composition_route: true`, three candidates, a valid transaction preview, five changed events, and only `set_pitch` operations.
- Rendered browser QA used the configured DeepSeek provider. The ordinary proposal tab displayed “Composer 自动路由”, “已评审 3 个候选”, “验证通过”, five pitch operations, and “未发现选区外意外修改”; the previous English refusal was absent. Browser console warnings/errors: 0. The verified proposal remained accessible at the normal desktop viewport and 720 x 900.
- Rebuilt the Windows `1.0.0-dev.8` package. The staged backend, compatibility desktop launcher, and Electron desktop executable all passed their packaged startup smoke tests.
- A direct request to the frozen packaged backend returned `generated`, `composition_route: true`, three candidates, a valid preview, eight changed events, and only `set_pitch` operations. Ports and packaged processes were released after verification.

### Unresolved

- V0.1 melody rewrite preserves the host rhythm and event inventory; insertion/deletion, duration rewrite, new parts, and instrument changes remain fail-closed.
- Explicit artistic direction still needs a bounded object such as melody, theme, motif, or harmony. Ambiguous aesthetic requests are not silently treated as authorization to rewrite notes.

### Paper impact

- Creative-intent routing can now be evaluated as an explicit orchestration layer: atomically specified edits use the strict LLM patch condition, while compositional edits use typed planning plus deterministic candidate realization under the same final transaction boundary.

## 2026-08-21 - Phase 22: Composer V0.2 style knowledge and local preference loop

### Completed

- Added a versioned, schema-validated Composer style knowledge base with seven bounded engineering profiles: classical, romantic, jazz, pop, minimal, modal, and cinematic. The store contains original rule summaries and traceable rule IDs; it does not copy book passages or copyrighted score excerpts.
- Replaced the planner's embedded progression table with retrieved style knowledge. Both deterministic and live high-level planning now report the knowledge-base ID, schema version, fingerprint, and matched rule IDs.
- Added read-only phrase analysis over the selected canonical `ScoreDocument`: primary voice, interval motif, contour, repetition/step ratios, register trajectory, and a source fingerprint. Analysis never mutates the host score.
- Expanded deterministic realization to a bounded internal search of up to 32 candidates. V0.2 ranks and diversity-selects candidates only after the existing transaction, protected-scope, rhythm, playability, voice-leading, motif, phrase, and style critics have run.
- Added local A/B preference feedback. It records only candidate IDs, aggregate critic scores, selected reason tags, style, and time; it stores no score notes, MusicXML, user identity, or API key. Duplicate feedback is idempotent, and preference can adjust only soft ranking weights, never safety validation.
- Added Composer knowledge, profile, and feedback endpoints plus candidate-comparison UI evidence. Users can compare theory, motif, phrase, style, playability, and preference scores before sending one candidate into the unchanged ScorePatch review boundary.
- Included the JSON knowledge assets in editable installs and PyInstaller builds, documented V0.2, and bumped the local Windows desktop package to `1.0.0-dev.9`.

### Main files

- `sera_edit/composer/style_kb/style_knowledge.schema.json`
- `sera_edit/composer/style_kb/style_knowledge.v0.2.json`
- `sera_edit/composer/style_knowledge.py`
- `sera_edit/composer/phrase_analysis.py`
- `sera_edit/composer/preference.py`
- `sera_edit/composer/candidate_generator.py`
- `sera_edit/composer/critics.py`
- `sera_edit/composer/pipeline.py`
- `sera_edit/composer/planner.py`
- `sera_edit/api/routes.py`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/score/scoreTypes.ts`
- `frontend/src/api.js`
- `tests/sera_edit/test_composer_v02_loop.py`
- `scripts/validate_style_knowledge.py`
- `docs/SERA_COMPOSER_V02.md`

### Tests and evidence

- Style-knowledge validator passed: schema `0.2.0`, seven styles, stable fingerprint `sha256:9cb730c63d0f824d64f2a0b75e6aa75c8191776a8f23279a929486a4bdbce381`.
- V0.2-specific backend suite: 14 passed, 0 failed. Broader Composer/API targeted suite: 38 passed, 0 failed.
- Full Python regression suite: 324 passed, 0 failed.
- Targeted Agent Console suite: 8 passed, 0 failed. Full frontend suite: 70 test files and 107 tests passed, 0 failed.
- Frontend production build passed with 214 transformed modules.
- Rendered browser QA imported a real host MusicXML fixture, generated three classical candidates from a 16-wide search, displayed style-knowledge and source-phrase evidence, and recorded one local motif/phrase preference. The host revision stayed at 0; no patch was applied. Browser console warnings/errors: 0. The normal desktop layout and 720 x 900 layout both passed, with no horizontal overflow.
- Rebuilt Windows `1.0.0-dev.9`. Staged backend, compatibility launcher, and Electron desktop startup smoke tests passed.
- Direct frozen-backend replay reported `1.0.0-dev.9`, knowledge base `0.2.0`, seven styles, 15 evaluated candidates, 12 valid candidates, and three returned classical candidates from real MusicXML.

### Unresolved

- Style profiles are bounded engineering priors and critic proxies, not proof that a candidate is aesthetically superior or historically authentic. Formal quality claims still require blind human listening/score-review evaluation.
- V0.2 realizes new melodic pitch material only over existing editable note events. Duration changes, insertion/deletion, new instruments, and structural orchestration remain fail-closed until their source-preserving host contracts are complete.
- The preference model is deliberately small and local. It improves ranking only after explicit user choices and does not train or fine-tune the remote LLM.

### Paper impact

- V0.2 adds reproducible experimental factors for retrieved style rules, source-motif conditioning, bounded candidate search, multi-critic ranking, and explicit local human preference while retaining the same protected transactional editing baseline.

## 2026-08-21 - Phase 23: Composer V0.3 large-corpus, small-context retrieval

### Completed

- Added a versioned Composer V0.3 atomic knowledge repository with four materialized JSONL packs and 266 project-authored rule cards. Cards cover harmony, melody, motif, phrase, cadence, rhythm, form, texture, dynamics, articulation, style grammar, orchestration, and instrument playability. The corpus contains no copied textbook passages or copyrighted score excerpts.
- Added a strict RuleCard schema, registry validation, path-bound pack loading, global rule-ID deduplication, stable corpus fingerprints, pack/domain/style/instrument statistics, and a deterministic pack builder/validator CLI.
- Implemented metadata plus lexical-IDF retrieval conditioned on the canonical score key/meter/tracks, target measures, requested style, planning mode, instruments, and creative goals. Selection adds style/instrument/goal coverage and domain diversity, then enforces both a maximum card count and deterministic estimated-token budget.
- Kept the complete corpus local. The high-level planning prompt receives only compact selected cards and retrieval evidence; it no longer receives the complete V0.2 style profile. Returned evidence explicitly records `full_corpus_sent_to_llm: false`, selected IDs, match reasons, query/corpus fingerprints, card counts, domains, estimated tokens, and budget.
- Preserved the V0.2 style profiles as local deterministic realization and critic parameters. V0.3 changes planning context and evidence only; it does not widen ScorePatch permissions or bypass transaction, protected-scope, source-fingerprint, rhythm, event-count, instrumentation, host-layout, or round-trip safeguards.
- Added `/sera-edit/composer/style-knowledge` corpus status without dumping cards. Updated the Agent UI to show total corpus size, selected card count, token estimate/budget, score/instrument/goal query facts, and an expandable list of only the retrieved rules.
- Included JSONL packs in editable installs, PyInstaller backend and desktop bundles. Bumped backend and desktop to `1.0.0-dev.10` and documented the V0.3 extension workflow.

### Main files

- `sera_edit/composer/knowledge_repository.py`
- `sera_edit/composer/knowledge_retrieval.py`
- `sera_edit/composer/style_kb/knowledge_registry.v0.3.json`
- `sera_edit/composer/style_kb/rule_card.schema.json`
- `sera_edit/composer/style_kb/packs/*.jsonl`
- `scripts/build_composer_knowledge_v03.py`
- `scripts/validate_composer_knowledge.py`
- `sera_edit/composer/planner.py`
- `sera_edit/composer/pipeline.py`
- `sera_edit/composer/style_knowledge.py`
- `sera_edit/api/routes.py`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/score/scoreTypes.ts`
- `tests/sera_edit/test_composer_v03_knowledge.py`
- `docs/SERA_COMPOSER_V03.md`

### Tests and evidence

- Knowledge build/validation passed with 266 unique cards across four packs and fingerprint `sha256:1db41eb638f460edab4620ebd1a7009f7d2d3aee8d184f4deba31283e891c299`.
- A 520 estimated-token smoke selected four rules using 451 estimated tokens. Default real Composer UI retrieval selected 12 of 266 cards using 1294/1800 estimated tokens; the full corpus was not sent.
- V0.3-specific and Composer regression selection: 30 passed, 0 failed. Full Python suite: 331 passed, 0 failed.
- Targeted Agent Console suite: 8 passed, 0 failed. Full frontend suite: 70 test files and 107 tests passed, 0 failed. Production frontend build passed with 214 transformed modules.
- Rendered browser QA connected a synthetic MusicXML host session, produced three classical piano candidates, showed the V0.3 corpus/query/budget evidence, and expanded all 12 selected rule cards with IDs and match reasons. No candidate was applied and host revision remained 0. Browser console warnings/errors: 0. Desktop layout passed; 720 x 900 reported no horizontal overflow.
- The first Electron packaging attempt encountered a transient TLS download disconnect. A cached retry succeeded, followed by a clean full `1.0.0-dev.10` rebuild. Staged backend, compatibility launcher, and Electron desktop smoke tests all passed.
- Direct frozen-backend replay reported version `1.0.0-dev.10`, knowledge schema `0.3.0`, 266 cards, four packs, two generated candidates, 12 selected rules, 1284/1800 estimated tokens, `full_corpus_sent_to_llm: false`, and prompt version `sera_composition_plan_v3.0`.

### Unresolved

- The corpus is a curated engineering prior, not proof of aesthetic quality or historical authenticity. Claims that candidates sound better still require blinded musician/listener evaluation.
- The current standard-library lexical index is appropriate for hundreds to low thousands of cards. At tens of thousands of cards, the repository interface should switch to a persistent inverted or local embedding index without changing the compact prompt contract.
- V0.3 does not enable structural orchestration edits. New instruments, new parts, duration changes, and event insertion/deletion remain fail-closed until the host/source-preserving contracts support them.

### Paper impact

- V0.3 makes knowledge retrieval an explicit reproducible factor: corpus fingerprint, query fingerprint, retrieval strategy, selected evidence, and context budget can be logged separately from the LLM and the unchanged transactional editing baseline.

## 2026-08-21 - Phase 24: actionable Composer rejection diagnostics and routing repair

### Completed

- Fixed a Chinese intent-boundary bug: the phrase `保持节奏和声部数量不变` previously matched the substring `和声` inside `和声部`, incorrectly turning an explicit melody rewrite into `reharmonize + preserve_melody`. Operation family is now server-owned, and `和声(?!部)` prevents the false harmony route.
- The candidate realizer now excludes explicitly protected events before search. A broader target can therefore modify its legal subset instead of generating patches that are guaranteed to fail E11. A fully protected target remains fail-closed with a precise diagnosis.
- Reharmonization with `preserve_melody` now excludes the detected primary voice even in a single-staff score. When no accompaniment remains, Sera returns `no_accompaniment_to_reharmonize` instead of silently rewriting the melody.
- Playability hard validation now compares stable before/after violation identities. A candidate may preserve or repair a pre-existing unconventional range/hand crossing, but is still rejected if it introduces a new range violation or crossing.
- Added structured `failure_analysis` with target/protected/editable counts, failed-layer counts, transaction error codes, bounded rejected examples, and actionable Chinese suggestions. Both Composer preview and the auto-routed patch channel preserve this evidence without exposing an unsafe patch.
- Added an Agent Console rejection panel for direct Composer and auto-routed proposal views. Updated the Composer V0.3 troubleshooting documentation and bumped backend/Electron to `1.0.0-dev.11`.

### Main files

- `sera_edit/composer/planner.py`
- `sera_edit/composer/candidate_generator.py`
- `sera_edit/composer/critics.py`
- `sera_edit/composer/pipeline.py`
- `sera_edit/generation/llm_patch_generator.py`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/score/scoreTypes.ts`
- `frontend/src/styles.css`
- `tests/sera_edit/test_composer_pipeline.py`
- `frontend/src/agent/__tests__/SeraAgentConsole.test.tsx`
- `docs/SERA_COMPOSER_V03.md`

### Tests and evidence

- Focused Composer/API regression suite: 38 passed, 0 failed. Full Python suite: 336 collected and passed, 0 failed.
- Targeted Agent Console suite: 9 passed, 0 failed. Full frontend suite: 70 test files and 108 tests passed, 0 failed. Production build passed with 214 transformed modules.
- Exact source regression using `重写当前选区的旋律，保持节奏和声部数量不变，并形成清晰终止。` returned `theory_variation`, evaluated 15 valid candidates, and returned three candidates.
- Rendered Browser QA used a real local bridge session with a single preserved melody. The UI displayed `no_accompaniment_to_reharmonize`, eight target notes, zero protected notes, and two actionable suggestions. Default desktop and 720 x 900 layouts passed; the narrow layout had `scrollWidth == clientWidth == 705`; Browser console warnings/errors: 0.
- Rebuilt Windows `1.0.0-dev.11`. Staged backend, compatibility launcher, and Electron desktop smoke tests passed. Frozen-backend replay reported `1.0.0-dev.11`, generated three melody-rewrite candidates, and returned the expected fail-closed diagnostic for single-line reharmonization.

### Unresolved

- Instrument-specific register limits still use conservative staff-role defaults in the current deterministic realizer/critic. Broader orchestral range handling should be derived from canonical instrument metadata before structural orchestration edits are enabled.
- The diagnostic explains why the current search failed; it does not weaken transaction, protected-scope, source-fingerprint, duration, notation-relation, or MusicXML round-trip checks.

### Paper impact

- The failure taxonomy is now observable at runtime and can support analysis of intent-routing errors, protected-target conflicts, transaction failures, and newly introduced playability conflicts without changing the safety baseline.

## 2026-08-22 - Phase 25: Composer V0.4 planning provenance, expectation, texture, and composition craft

### Completed

- Audited the latest real MuseScore bridge session rather than inferring quality from the green transaction state. The displayed `classical / melody_accompaniment / I-IV-ii-V / preserve_contour / 20-34-48-68` plan exactly matched the local classical defaults; the old response stored no request ID or planner trace, so a configured provider could not be treated as proof that the plan came from the LLM.
- Added a deterministic MusicXML audit CLI and ran it on the actual source and reviewed revision for M1-M4. The source contains 64 selected notes and four active voices. The symbolic texture classifier identified `melody_accompaniment` with confidence 0.8955 and primary voice `right_hand:v1`.
- Connected the existing melody-expectation validator to Composer ranking and repair. The real reviewed revision fell from source proxy 0.8800 to 0.6717, added six primary-line large leaps, reduced post-skip reversal to 0.1667, and increased unresolved dissonance count from three to seven. This is evidence of a weak structural melody candidate, not a human aesthetic judgment.
- Added three V0.4 knowledge packs: 24 melodic-expectation cards, 28 texture-structure cards, and 40 composition-craft cards. The complete local corpus now has 358 unique cards across seven packs. Retrieval remains capped at 12 cards and 1800 estimated tokens, and now caps any one domain at four selected cards so one broad topic cannot crowd out style, harmony, texture, or expectation.
- Added scoped symbolic texture analysis over active voices, attack alignment, rhythmic independence, track role, register separation, and density. Source texture and target plan texture are reported separately; the heuristic does not claim audio-level or work-wide classification.
- Added privacy-bounded Composer run traces under `%LOCALAPPDATA%\Sera\composer_runs.v0.4.jsonl` plus `/sera-edit/composer/latest-run`. Traces record planner kind, provider/model/request ID/token/latency/fallback, plan, selected rule IDs, scope/fingerprint, texture/phrase summaries, and candidate aggregate reviews, but not API keys, MusicXML, note/event content, or patches.
- Updated the Agent UI to distinguish `本次高层计划：实时 LLM` from `本次高层计划：本地理论回退`, show fallback reason and request evidence, display source/target texture, and label a valid candidate as passing safety checks rather than all musical checks.
- Fixed critic comparison to use the transaction-materialized diff. This prevents derived MusicXML beam metadata from being mistaken for an unauthorized candidate edit after a source re-import.
- Added expectation-aware bounded primary-line repair. A repair is retained only when the proxy improves and all existing source-fingerprint, target/protected-scope, event-count, rhythm, instrumentation, notation, playability, transaction, and round-trip safeguards continue to pass.
- Bumped the planning prompt to `sera_composition_plan_v4.0` and the backend/Electron package to `1.0.0-dev.12`.

### Main files

- `sera_edit/composer/texture_analysis.py`
- `sera_edit/composer/knowledge_retrieval.py`
- `sera_edit/composer/knowledge_repository.py`
- `sera_edit/composer/style_kb/knowledge_registry.v0.4.json`
- `sera_edit/composer/style_kb/packs/melodic_expectation.jsonl`
- `sera_edit/composer/style_kb/packs/texture_structure.jsonl`
- `sera_edit/composer/style_kb/packs/composition_craft.jsonl`
- `sera_edit/composer/planner.py`
- `sera_edit/composer/candidate_generator.py`
- `sera_edit/composer/critics.py`
- `sera_edit/composer/pipeline.py`
- `sera_edit/composer/run_trace.py`
- `backend/generation/musicality/melody_expectation_validator.py`
- `sera_edit/api/routes.py`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/score/scoreTypes.ts`
- `frontend/src/styles.css`
- `scripts/build_composer_knowledge_v04.py`
- `scripts/audit_composer_musicxml.py`
- `tests/sera_edit/test_composer_v04_theory.py`
- `docs/SERA_COMPOSER_V04.md`

### Tests and evidence

- Knowledge build and validation passed: schema `0.4.0`, 358 cards, seven packs, fingerprint `sha256:9493d177ea39355986d7473ad04a49518737cd3d3fc153395ff98d238eba33a9`.
- Focused Composer V0.2-V0.4 regression selection: 39 passed, 0 failed. Full Python suite: 340 collected and passed, 0 failed.
- Targeted Agent Console suite: 9 passed, 0 failed. Full frontend suite: 70 test files and 108 tests passed, 0 failed. Production build passed with 214 transformed modules.
- Same-source local replay returned three transaction-valid candidates. Candidate 1 scored 0.8950 on the melody-expectation proxy versus source 0.8800, preserved `melody_accompaniment`, and retrieved 12/358 cards using 1413/1800 estimated tokens. Candidates 2 and 3 scored 0.8417 and 0.8400, demonstrating that hard validity alone does not erase ranking differences.
- Rendered local Browser QA reached a ready dev.12 backend, displayed the configured DeepSeek provider separately from execution provenance, imported the real source MusicXML into a non-destructive host session, and showed no browser-console errors. A second live LLM request was deliberately not sent during QA because it would transmit score-derived context and was unnecessary to validate the provenance UI.
- Built an isolated Electron `win-unpacked` package at `dist_desktop/release-dev12/win-unpacked/Sera.exe` without stopping or overwriting the user's running dev.11 session. Direct frozen-backend smoke reported version `1.0.0-dev.12`, knowledge V0.4 with 358 cards/seven packs, prompt `sera_composition_plan_v4.0`, three local candidates, top expectation 0.8950 versus source 0.8800, and preserved texture.

### Unresolved

- The Huron/tessitura features are auditable engineering proxies, not a reproduction of ITPRA, a universal melodic law, or a proof that a candidate sounds better. Formal quality claims require blinded musician review, listening, and preferably performer feedback.
- The texture classifier describes symbolic attack patterns only inside the selected scope. Sustained overlap, timbre, perceptual streaming, and time-varying local texture still need richer analysis.
- The current host contract continues to allow bounded pitch realization over existing events only. Duration rewriting, insertion/deletion, new parts, and structural orchestration remain fail-closed.
- The audited old task lacks historical request evidence, so it cannot be retroactively classified as a live LLM plan. New requests are traceable.

### Paper impact

- V0.4 adds planner provenance, retrieval evidence, scoped texture descriptors, source-relative melody-expectation proxies, and a real failure case suitable for error analysis. These are reproducible engineering measures; they do not replace the paper's required task-success, preservation, structural-validity, and human-review evidence.

## 2026-08-22 - Phase 26: non-blocking Composer LLM refinement

### Completed

- Diagnosed the unusable latency as an orchestration problem rather than a MusicXML or candidate-validator failure: automatic Composer preview synchronously waited up to 30 seconds for the live high-level plan before it started local candidate search; the frontend held the interaction for up to 45 seconds. The user's general provider configuration also allowed 90 seconds and 4000 output tokens, although a compact composition plan does not need that output budget.
- Replaced the synchronous automatic path with a two-stage response. Sera starts a bounded daemon LLM refinement job and immediately performs a reduced-width deterministic local search. The initial response contains safe local candidates plus a credential-free refinement ID; it no longer waits for the provider.
- Added a read-only refinement endpoint and a 1.2-second frontend poll. A valid live plan automatically replaces the displayed candidates. Provider timeout, HTTP failure, invalid JSON, invalid plan, or a full job queue retains the local candidates and reports the failure without disabling review.
- Added Composer-specific runtime bounds: 30-second background timeout and 512 maximum output tokens by default, independently configurable through `SERA_COMPOSER_LLM_TIMEOUT_SECONDS` and `SERA_COMPOSER_LLM_MAX_OUTPUT_TOKENS`. The frontend initial preview timeout is now 20 seconds because it only covers deterministic local search.
- Preserved the complete ScorePatch safety baseline. Neither the local draft nor the later LLM refinement can apply a score; the user must select a candidate and pass the same source-fingerprint, transaction, target/protected-scope, rhythm, event-count, notation-relation, playability and MusicXML round-trip checks.
- Bumped backend and Electron to `1.0.0-dev.13`, added operator documentation, built an isolated Windows package, and verified that the frozen backend exposes both responsive preview and refinement polling routes.

### Main files

- `sera_edit/composer/refinement.py`
- `sera_edit/composer/pipeline.py`
- `sera_edit/api/routes.py`
- `frontend/src/api.js`
- `frontend/src/score/scoreTypes.ts`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/styles.css`
- `tests/sera_edit/test_composer_pipeline.py`
- `.env.example`
- `docs/SERA_COMPOSER_RESPONSIVE.md`

### Tests and evidence

- Focused Composer/API regression suite: 36 passed, 0 failed. The new blocking fake-provider test verifies that the local result returns while the provider remains blocked, that the background result later becomes ready, and that the LLM plan is capped at 512 output tokens.
- Full Python suite: 342 collected and passed, 0 failed. Targeted Agent Console suite: 9 passed, 0 failed. Full frontend suite: 70 test files and 108 tests passed, 0 failed. Production frontend build passed with 214 transformed modules.
- Real local replay on the user's M1–M4 source evaluated eight candidates, returned three transaction-valid candidates, and completed in 3.913 seconds.
- Rendered Browser QA used the real local source and an OpenAI-compatible stub with a fixed eight-second delay. The UI first showed three local safe candidates and a running refinement notice; it later changed to `实时 LLM`, reported 8358 ms plus request ID `slow_stub_request_1`, kept three candidates, and allowed candidate 1 to enter a `验证通过` final proposal. No host revision was applied.
- Built `dist_desktop/release-dev13/win-unpacked/Sera.exe`. Frozen-backend smoke reported `1.0.0-dev.13`, `v1_notation_editing_layer`, local-rule fallback readiness, and both `/sera-edit/composer/preview` and `/sera-edit/composer/refinements/{job_id}` in OpenAPI.

### Unresolved

- The live DeepSeek service was not called during this validation, avoiding API cost and transmission of score-derived context. Real provider latency still depends on the chosen model, network and service load, but it no longer blocks access to local candidates.
- Background jobs are intentionally process-local and short-lived. They do not survive application restart and are not a durable distributed queue.
- Reduced-width local search improves response time but does not prove that the candidate is aesthetically superior. Formal musical-quality claims still require blinded score/listening review.

### Paper impact

- Phase 26 separates time-to-first-safe-candidate from live-provider completion latency and preserves provider provenance for the later refinement. These can be reported as distinct reproducible latency components without changing the structured-patch safety condition.

## 2026-08-22 - Phase 27: DeepSeek completion and source-adaptive playability

### Completed

- Reproduced the user's exact M1–M8 failure over 129 target notes and five staff/voice streams. The previous fixed left/right pitch bounds introduced crossings in measures that were separated in the source, causing all 16 candidates to be rejected as `new_playability_conflicts`.
- Added source-adaptive per-measure staff bounds. Measures with a pre-existing safe hand gap retain a boundary inside that gap; pre-existing crossing measures remain source-relative so the validator only rejects newly introduced problems.
- Separated the Composer background timeout from the general provider timeout, exposed a 30–600 second in-app setting, and set the default to 180 seconds. Initial local candidates remain non-blocking.
- Reduced the high-level planner context from event-level score data to immutable global, scope, count, voice and instrument summaries. The LLM still receives the retrieved small knowledge context but no event IDs or event pitches.
- Added DeepSeek JSON Object mode and an explicit output example. Because DeepSeek V4 Pro defaults to thinking mode and twice consumed the exact 512/2048 output-token ceiling without producing parseable JSON, Composer planning now explicitly disables thinking for this narrow server-validated JSON request only. Normal conversation reasoning settings remain unchanged.
- Improved the Agent Console refinement state so a local rejection is not presented as the final LLM answer while live planning is still running, transient poll failures are retried, and the independent Composer timeout is visible.
- Bumped backend and Electron to `1.0.0-dev.14` and updated responsive Composer operator documentation.

### Main files

- `sera_edit/composer/candidate_generator.py`
- `sera_edit/composer/planner.py`
- `sera_edit/composer/pipeline.py`
- `sera_edit/providers/openai_compatible.py`
- `sera_edit/providers/runtime.py`
- `sera_edit/api/routes.py`
- `frontend/src/agent/SeraAgentConsole.tsx`
- `frontend/src/agent/LLMProviderSettingsDialog.tsx`
- `tests/sera_edit/test_composer_pipeline.py`
- `tests/sera_edit/test_provider_and_runtime_controls.py`
- `tests/sera_edit/test_api_routes.py`
- `frontend/src/agent/__tests__/SeraAgentConsole.test.tsx`
- `packaging/windows/build_windows_app.ps1`
- `packaging/windows/smoke_test_packaged_app.ps1`
- `run_app.bat`
- `scripts/create_desktop_shortcut.ps1`
- `.env.example`
- `docs/SERA_COMPOSER_RESPONSIVE.md`

### Tests and evidence

- Focused Composer/provider/API tests: 39 passed, 0 failed. Targeted Agent Console tests: 9 passed, 0 failed. Production frontend build passed with 214 transformed modules.
- Full Python regression suite: 345 passed, 0 failed. Full frontend suite: 70 test files and 108 tests passed, 0 failed.
- Exact local source replay before the playability change evaluated 16 candidates and rejected all 16. After the change, the same width-16 replay evaluated 16, validated 16, returned three, and introduced zero new staff crossings or range violations.
- Responsive local replay of the same source returned in 12.055 seconds: eight evaluated, eight valid, zero rejected, three returned.
- A real DeepSeek V4 Pro trace before the final fix used 2969 input tokens and exactly 2048 output tokens, then failed JSON parsing after 35.940 seconds. With DeepSeek non-thinking JSON mode, the same source used 2890 input and 174 output tokens, returned a valid live plan in 4.347 seconds, evaluated 12 candidates, validated 12, rejected zero, and returned three. Request ID: `d75efa20-a44f-4542-b7e6-724fd9817c3b`.
- Rendered local Browser QA loaded the real M1–M8 host session, showed the configured DeepSeek model and the in-app 180-second Composer timeout, and produced no browser console warnings or errors. The live provider call was verified separately through the real HTTP endpoint so UI inspection did not transmit the score a second time.
- Built `dist_desktop/release-dev14/win-unpacked/Sera.exe`. The staged backend, compatibility launcher and isolated Electron package all passed runtime smoke checks. The frozen backend reported `1.0.0-dev.14`, the configured `deepseek-v4-pro`, a 180-second Composer timeout, and both preview/refinement routes. The standard desktop shortcut now resolves through `run_app.bat` to the dev.14 package.

### Unresolved

- Provider latency still varies with network and service load. The 180-second setting prevents premature cancellation but is not a latency guarantee.
- Non-thinking JSON mode is intentionally limited to the narrow high-level plan. It improves completion reliability but does not establish musical superiority.
- The candidate generator still rewrites pitch over the existing rhythmic/event scaffold; insertion, deletion, new parts and structural orchestration remain fail-closed.

### Paper impact

- Phase 27 provides a reproducible real-provider truncation failure and repair case, plus a source-relative multi-staff playability regression. The evidence supports reliability and latency engineering claims only; aesthetic quality still requires blinded human evaluation.

## 2026-08-23 - Phase 28: independent SoftwareX release and verification track

### Completed

- Added an independent `paper/softwarex` and `docs/softwarex` release track without
  replacing or weakening the ICMC structured-patch research baseline.
- Added MIT software licensing, CC0 benchmark separation, citation/code metadata,
  dependency-rights inventory, installation/user/API/reproducibility documentation,
  SoftwareX v4 manuscript assets, architecture exports, submission statements, release
  packaging and strict readiness gates.
- Ran a fresh 120-task/three-condition offline fixture verification and preserved its
  raw/normalized outputs, manifest and metrics as explicitly non-formal evidence.

### Tests and evidence

- Core benchmark: 120 valid, 0 invalid, 120 pending human review.
- Verification experiment: 360/360 complete, 0 execution errors; all seven drift and
  evidence checks passed; `formal_results_allowed=false`.
- Full Python suite: 350 collected and passed. Frontend: 70 files/108 tests passed;
  production build passed with 214 modules. dev.14 staged backend, launcher and Electron
  package smoke passed.
- Draft SoftwareX verifier passed with 1368 main-text words, 105-word abstract, six
  keywords, one figure, coherent version/license metadata and complete local assets.

### Unresolved and paper boundary

- The SoftwareX submission is not publicly ready until author identity/support data,
  copyright-owner MIT confirmation, a public tagged GitHub release and a permanent
  archive DOI are supplied. No commit, tag, push or external submission was performed.
- Local LaTeX PDF compilation remains pending a TeX Live/Overleaf environment; the
  line-numbered DOCX and v4 LaTeX source are both present.
- Mock fixture success is not LLM performance, and automatic benchmark validity is not
  human musical-quality validation.

## 2026-08-23 - Phase 29: local benchmark review and conditional aesthetics gate

### Completed

- Added a local three-column review workspace for the 120-task core benchmark. It
  exposes task filters, bilingual instructions, target/protected scope, Gold operations,
  automatic evidence and deterministic event-level diffs without reintroducing an
  internal notation editor.
- Added source/expected MusicXML preparation and a path-restricted Electron bridge so
  visual review remains in MuseScore, Sibelius or another MusicXML-associated host.
- Added append-only, fingerprinted primary/secondary decisions under the per-user Sera
  data root, plus bounded ratings/issues, progress/category summaries and JSON/CSV export.
- Separated batch benchmark repair from aesthetic calibration. Either gate waits for 20
  primary decisions and a 20% failure rate; the aesthetic gate additionally requires an
  explicit musical-validity failure, so selector/Gold problems cannot be mislabeled as
  taste failures.
- Added the SoftwareX human-review protocol: 120 primary decisions, a stratified 30-task
  second-review sample and, only if triggered, a 24-pair blinded Composer preference
  calibration cycle followed by the unchanged ScorePatch safety pipeline.

### Tests and evidence

- All 120 tasks produced fingerprinted detail records with valid automatic evidence;
  the benchmark validator again reported 120 valid and 0 invalid.
- Focused review backend/API tests: 6 passed. Review component tests: 3 passed.
- Full Python suite: 356 passed. Full frontend suite: 71 files and 111 tests passed.
  Production frontend build passed with 215 transformed modules. Electron main/preload
  syntax checks passed.
- Rendered local QA traversed Agent -> Research review -> core task -> save -> next task.
  Progress moved from 0/120 to 1/120 in an isolated review directory, `conflict_002`
  became the next evidence view, and the browser console reported no warnings/errors.
- Built `dist_desktop/release-dev14-review/win-unpacked/Sera.exe`. The packaged backend,
  compatibility launcher and Electron runtime passed smoke; the frozen review API
  reported 120 total tasks, 120 remaining and 15 pitch-transposition tasks.
- Updated `run_app.bat` to launch the review-enabled package first, with the previous
  dev.14 build retained as a fallback.

### Unresolved and paper boundary

- Formal human review remains 0/120; the isolated QA decision is not part of the real
  review store. Automatic validation and UI testing do not establish expert validation.
- Aesthetic fitting has not started because the minimum human evidence gate has not been
  reached. The interface describes and activates the existing preference-calibration
  cycle only after qualifying musical failures; it never auto-trains on compliance data.

## 2026-08-23 - Phase 30: meter-task semantic repair and host-visible validation

### Completed

- Reproduced `meter_001` in MuseScore Studio 4.5.2 and confirmed the original Gold only
  changed the displayed value from 4/4 to 2/2, leaving an artistically indistinguishable
  event structure. Replaced it with an explicit 4/4-to-3/4 rebar task that deletes the
  final quarter-note event from both staves in each of three measures while preserving
  every remaining pitch and duration.
- Corrected canonical MusicXML export so persistent dynamics are emitted only on the
  first event and actual changes per staff/voice, rather than printing `mf` under every
  note. Moved the metronome direction inside the first measure for valid host structure.
- Regenerated all 20 source and 110 expected MusicXML files from their authoritative
  ScoreDocuments. Clarified the remaining meter tasks as signature-only changes that do
  not claim rebaring or beat regrouping.
- Strengthened benchmark validation to re-import the checked-in source and expected
  MusicXML, compare it with canonical JSON, and run deterministic task constraints on
  the host-facing representation.
- Invalidated stale human decisions by task fingerprint while retaining them in the
  append-only audit log; the UI now reports old records that require re-review.

### Tests and evidence

- MuseScore 4.5.2 host render shows 3/4, 19 remaining events, six expected deletions and
  one `mf` per staff. The packaged meter-fix backend reported 4/4 -> 3/4, seven changed
  elements, six deletions and two MusicXML `mf` marks.
- Core benchmark validation: 120 valid, 0 invalid. Full Python suite: 359 tests passed.
  Frontend: 71 files and 111 tests passed; production build completed with 215 modules.
- Built `dist_desktop/release-dev14-meterfix/win-unpacked/Sera.exe` without terminating
  the review-enabled Sera instance that was open during repair.

### Unresolved and paper boundary

- `meter_001` must be manually reviewed again; any decision made against its old task
  fingerprint is retained for audit but excluded from progress and analysis.
- A host render is evidence that this fixture imports correctly in MuseScore 4.5.2, not
  a claim of universal MusicXML compatibility or general automatic rebaring.

## 2026-08-23 - Phase 31: Chinese task-code standards and refusal semantics

### Completed

- Added an in-product Chinese standards table for all ten benchmark task-ID families.
  It states the ID range, category meaning, expected success/refusal state, required
  result and protected properties; numeric suffixes are explicitly defined as serial
  numbers rather than measure numbers, difficulty or expected change counts.
- Added a task-specific compliance card generated from the current deterministic
  constraints. Known constraint and refusal codes are translated into Chinese instead
  of requiring reviewers to infer semantics from JSON or English instructions.
- Made refusal evidence unambiguous: `conflict_*` tasks label the expected host file as
  the unchanged post-refusal source, and explain that zero event-level changes are the
  correct result. Documented `conflict_001` as an intentional incompatibility between
  5/8, fixed existing durations and the prohibition on rests.
- Added the same normative table to the benchmark card and SoftwareX human-review
  protocol so the review interface and published methodology use one interpretation.

### Tests and evidence

- Focused review component tests: 5 passed, including all ten code-family rows and the
  `conflict_001` zero-diff refusal explanation.
- Full frontend suite: 71 files and 113 tests passed. Production build passed with 215
  transformed modules; the core benchmark remained 120 valid and 0 invalid.
- Rendered QA exercised Agent -> Research review -> Number standards -> `conflict_001`.
  The table contained all ten families, the task card exposed the translated refusal
  constraint and unchanged-score rule, and browser console warnings/errors were empty.
- Prepared `dist_desktop/release-dev14-standards-final/win-unpacked/Sera.exe` by cloning
  the already verified meter-fix runtime and replacing only the built frontend resource.
  Package inspection found both new Chinese markers; its frozen backend passed health,
  120-task summary and `conflict_001` refusal/zero-diff API smoke on an isolated port.

### Unresolved and paper boundary

- The table explains deterministic benchmark contracts; it does not replace host score
  inspection or turn the 120 pending tasks into human-verified data.
- Prefix-level descriptions are navigation aids. The current task instruction, scope
  and deterministic constraints remain authoritative when task instances differ.

## 2026-08-23 - Phase 32: Gold-review versus live-model failure clarification

### Completed

- Investigated the reported latest-task rejection against the running desktop process,
  review audit and live APIs. The active task was `conflict_005`; it has the deterministic
  Gold contract `expected_status=refuse`, `meter_duration_conflict` and zero changes.
  The four preceding conflict tasks were saved as compliant primary reviews. No LLM is
  invoked by task navigation, Gold artifact preparation or review submission.
- Corrected the review surface so it cannot imply a provider failure: the header now
  says that the page does not call an LLM, the validation badge says “benchmark contract,”
  each task exposes “model call: none,” and refusal evidence explicitly distinguishes a
  Gold rejection from timeout, empty response or malformed model output.
- Clarified the same boundary in the benchmark card and human-review protocol. Model
  performance remains the responsibility of the separately recorded three-condition
  experiment, not the Gold-review workspace.

### Tests and evidence

- Focused review component tests: 5 passed. Full frontend suite: 71 files and 113 tests
  passed. Production build passed with 215 modules; core validation remained 120/120.
- Rendered QA selected the actual pending `conflict_005` after four saved reviews and
  verified all new boundary labels. The browser console contained no warnings/errors.
- Prepared `dist_desktop/release-dev14-review-clarity/win-unpacked/Sera.exe`; package
  inspection found all three new labels, and the frozen backend passed health plus
  `conflict_005` refusal/zero-diff API smoke on an isolated port.

### Unresolved and paper boundary

- The currently open desktop instance still runs the earlier meter-fix package. Saved
  reviews are append-only and safe, but the user must close all Sera windows and relaunch
  through `run_app.bat` before the clarified frontend becomes active.
- This correction prevents a Gold label from being mistaken for model behavior; it does
  not convert Gold review into an LLM evaluation or alter any benchmark task.

## 2026-08-23 - Phase 33: `dynamics_001` latency and constraint repair

### Completed

- Corrected the reported sixth review item to `dynamics_001` and reproduced its exact
  interactive request against the configured DeepSeek runtime. The pre-fix path took
  34.818 seconds and two model attempts because the first transport proposal required
  an LLM repair before producing the one-event `set_dynamic` operation.
- Added local-first routing for explicit event-ID dynamics and articulation edits. These
  deterministic notation operations now compile directly into the same strict,
  source-bound ScorePatch; broader editing requests still use the configured model, and
  formal Full Rewrite / Patch Only / Sera Full experiment runners are unchanged.
- Disabled DeepSeek thinking mode for the bounded interactive patch request and its one
  repair request. This applies only to the small server-validated planning contract and
  does not change Composer or conversational reasoning settings.
- Added the missing `preserve_duration` deterministic constraint to `dynamics_001` and
  its Batch 1 generator. Its Gold MusicXML remains semantically explicit: `mf` at the
  initial note, `f` at `m1_rh_3`, and restoration to `mf` at `m1_rh_4`.

### Tests and evidence

- Focused live-generator and API tests passed 16/16; the complete `tests/sera_edit`
  suite passed all 150 tests.
- Core benchmark validation passed 120/120 with MusicXML round-trip and deterministic
  constraints enabled.
- A development HTTP regression completed in 0.539 seconds. The rebuilt frozen backend
  completed the same request in 0.451 seconds with zero provider calls, routing
  `local_first`, one `set_dynamic` operation on `m1_rh_3`, one changed element and a
  valid transaction report.
- Built the isolated desktop package at
  `dist_desktop/release-dev14-dynamicsfix/win-unpacked/Sera.exe`; `run_app.bat` now
  prefers it while retaining the review-clarity and base dev.14 packages as fallbacks.

### Unresolved and paper boundary

- The local-first latency measurement is an interactive product regression result, not
  a formal LLM benchmark observation and must not be mixed into the three-condition
  paper metrics.
- `dynamics_001` remains pending human score review. Automatic validation establishes
  contract and MusicXML consistency, not a musician's acceptance of the notation.

## 2026-08-23 - Phase 34: `key_001` executable key-signature edit and global-diff repair

### Completed

- Reproduced the reported `key_001` discrepancy and separated two defects from the
  benchmark contract. The Gold task and expected MusicXML already required C major to
  G major with all pitches preserved, but the interactive generator did not support a
  key-signature operation and the review table hid global before/after values as dashes.
- Added a bounded local compiler for explicit English/Chinese key-signature commands.
  A whole-score request now emits one strict `change_key_signature` operation and uses
  the existing fingerprint, transaction, validation and preview pipeline without
  transposing any note. Ambiguous harmony or transposition requests are not reclassified.
- Added local-first routing for exact whole-score key edits. Broader edits still use the
  configured LLM, and the formal Full Rewrite, Patch Only and Sera Full experiment
  conditions are unchanged.
- Corrected the review renderer so global key and meter rows display their actual values.
  `key_001` now visibly reports `C major` before and `G major` after.

### Tests and evidence

- Focused rule/live/API tests passed 22/22; the complete `tests/sera_edit` suite passed
  152/152. The full frontend suite passed 114 tests in 71 files, and the production
  build completed with 215 transformed modules.
- Core benchmark validation remained 120 valid and 0 invalid. Rendered review QA at
  1280x720 showed the global row as `C major -> G major`; browser console warnings and
  errors were empty.
- The rebuilt frozen backend returned the exact request in 0.396 seconds with provider
  `local_rule`, routing `local_first`, a valid transaction, one global changed element,
  and all 16 pitch events unchanged. Its review API returned the same before/after keys.
- Built `dist_desktop/release-dev14-keyfix/win-unpacked/Sera.exe`; the normal launcher
  now prefers this isolated package and retains earlier packages as fallbacks.

### Unresolved and paper boundary

- This deterministic interactive regression is product evidence, not an LLM experiment
  observation, and must not be mixed into the three-condition paper metrics.
- `key_001` still requires human host-score review. Round-trip and frozen API evidence
  establish the specified MusicXML semantics, not universal notation-host rendering.

## 2026-08-24 - Phase 35: host-selection scope resolution for global key edits

### Completed

- Reproduced the user's exact running-desktop request, `将调号改为G major，但不要移调音符。`,
  with the MuseScore M1-M2 host scope. The previous package sent it to DeepSeek because
  local-first routing incorrectly required the incoming scope to already be whole-score;
  DeepSeek then correctly followed the obsolete interactive whitelist and refused it.
- Added explicit scope resolution for key signatures. A key-signature-only instruction
  now records the requested host scope, promotes the effective target to whole-score,
  and retains `preserve_pitch` and transaction validation. Mixed or ambiguous requests
  are not silently promoted.
- Changed local-first detection to inspect the server-resolved patch scope, so the exact
  global operation bypasses the slower remote planner while still recording the
  configured provider. The patch provenance records the scope-resolution decision.
- Corrected the proposal review surface to describe key/time signature operations as
  whole-score edits, display the scope-promotion notice, and include global changes in
  its element counts instead of incorrectly showing zero total edits.

### Tests and evidence

- Focused rule/live/API tests passed 25/25; the complete `tests/sera_edit` suite passed
  155/155. Core benchmark validation remained 120 valid and 0 invalid.
- The full frontend suite passed 115 tests in 71 files and the production build completed
  with 215 transformed modules. Rendered Browser QA exercised host session -> 修改提案
  -> the exact Chinese request -> generated review. It showed 验证通过, 全谱 key G major,
  全局 1 and no unsupported state; browser warnings/errors were empty.
- Development HTTP returned in 0.516 seconds. The rebuilt frozen backend returned in
  0.335 seconds with `local_rule`, requested provider `deepseek`, routing `local_first`,
  valid preview, C major -> G major, one global change and all 16 pitches preserved.
- Built `dist_desktop/release-dev14-keyscopefix/win-unpacked/Sera.exe`; `run_app.bat`
  now prefers this isolated package while retaining `keyfix` and older fallbacks.

### Unresolved and paper boundary

- Scope promotion is limited to an explicit key-signature-only operation because the
  property is global in the canonical score. It is recorded and visible, not a general
  authorization for the Agent to broaden arbitrary host selections.
- The active desktop process still runs the previous `keyfix` package. The user must
  close every Sera process/window before relaunching because Electron single-instance
  handling can otherwise focus the old process.

## 2026-08-24 - Phase 36: bilingual 120-task runtime acceptance closure

### Completed

- Added a resumable runtime-acceptance runner that replays benchmark instructions through the
  actual interactive patch-generation entrypoint, dry-run validation, committed transaction,
  constraint evaluation and MusicXML round trip. It stores raw generation, preview, transaction,
  fingerprints, timing and host-openable outputs for each task-language-repetition run.
- Retained the initial `32/120` baseline as failure evidence, then extended the auditable local
  compiler and fixed generator-ID-independent constraint/minimality evaluation. English reached
  `120/120`; the first bilingual run exposed 39 Chinese parsing gaps, which were repaired rather
  than hidden or removed from the benchmark.
- The final run `runtime_acceptance_core_bilingual_r3_v1_20260824` completed `720/720` runs:
  120 tasks, English and Chinese, three repetitions. There were 660 safe executable outputs,
  60 correct refusals, zero unsafe executions, full deterministic constraint satisfaction,
  MusicXML validity and protected-scope preservation. All 240 repeated task-language groups had
  identical patch and post-score fingerprints. Resume re-entry completed without duplicate rows.
- Cross-language comparison exposed 22 result mismatches that the task constraints did not
  catch: Chinese `保持音高` was incorrectly parsed as tenuto. The parser now requires the
  explicit term `保持音记号`; a fresh v2 replay passed `720/720` and all `120/120` task
  groups now have semantically equivalent patches and identical English/Chinese outputs.
- Integrated acceptance evidence into the human-review workspace with failure-first ordering,
  filters and direct opening of Sera's English/Chinese host outputs. Added a compact publication
  snapshot with hashes for all 1,380 original evidence files and 220 review outputs.

### Tests, interface and package evidence

- Passed the full 163-test SeraEdit suite and all 373 project Python tests, all 116 frontend
  tests in 71 files, the 215-module build and deterministic core validation at `120/120`.
- Rendered local QA verified the 120/120 and 720-run summary, the empty failure filter,
  per-task 6/6 badges, refusal-specific non-transaction wording, both language artifacts and
  no browser console warnings or errors.
- Built `dist_desktop/release-dev14-runtimeacceptance/win-unpacked/Sera.exe`. Frozen smoke now
  fails unless the package itself can load all 120 task statuses, all 720 run rows and prepare
  a Chinese runtime MusicXML. Backend, compatibility launcher and Electron shutdown passed.
- Replaced a corrupted review-protocol section with valid UTF-8 bilingual instructions and
  refreshed the SoftwareX manuscript DOCX and deterministic archives.

### Research boundary and next phase

- Runtime acceptance is explicitly non-formal product evidence. It uses the strict local runtime
  compiler and deterministic benchmark constraints; it must not be reported as LLM model accuracy
  or artistic preference. Gold patches were not used to generate the proposals.
- Human host rendering/musical review, the three-condition live-provider experiment and public
  release metadata remain separate requirements. Automatic `720/720` results make human review
  faster but do not mark any task as human reviewed.

## 2026-08-25 - Phase 37: host-selection localization regression closure

### Completed

- Reproduced `compound_001` with a MuseScore-style M2-M3 selection. The previous rule
  compiler chose the positional "final two notes" over the complete selection and therefore
  generated M3 event IDs despite the instruction explicitly naming measure 2.
- Added a deterministic instruction-scope resolver for English/Chinese measure and staff
  locations. The effective patch scope is the intersection of instruction location and host
  selection; it can narrow but never broaden host authorization. Out-of-selection locations
  are rejected, and requested/effective/excluded scopes are recorded in provenance.
- Integrated the resolver into local and live planning while preserving the audited global
  key/time-signature scope path. Added exact transaction/API regressions for M2-M3, stable
  event-ID filtering, live-provider prompts, Chinese parity and fail-closed behavior.
- Added adjacent-measure pressure testing to the product acceptance runner. The 240-run
  bilingual robustness experiment passed completely, including 174/174 actual widened-host
  cases. The fresh 720-run bilingual repeated baseline also passed completely with semantic
  and output cross-language equivalence at 120/120 and repeat fingerprints at 240/240.

### Tests and delivery evidence

- Passed all 171 SeraEdit tests and 381 project Python tests, 116 frontend tests, the frontend
  production build and 120/120 benchmark validation. Human review remains pending for 120 tasks.
- Updated SoftwareX evidence snapshots, verifier, reproducibility documentation and manuscript.
  Draft package verification passes and now checks both the 720-run baseline and 240-run
  localization robustness evidence.
- Built the isolated `release-dev14-scopefix` desktop package. Staged backend, legacy launcher
  and Electron lifecycle smoke passed. A frozen-backend HTTP replay resolved host M2-M3 to M2,
  changed only `s007_m2_rh_3`/`s007_m2_rh_4`, and reported no M3 change.

### Research boundary

- This is deterministic product and regression evidence, not a formal LLM comparison or
  aesthetic-quality result. It does not replace blinded human inspection of the 120 tasks.

## 2026-08-25 - Phase 38: Windows frozen-runtime temp-residue closure

### Completed

- Replaced the PyInstaller one-file backend and legacy compatibility launcher with onedir
  distributions. Frozen Sera processes now run from their packaged directories instead of
  extracting roughly 0.5 GiB into `%TEMP%\_MEI*` on every launch.
- Updated Windows staging to copy each complete onedir distribution while preserving the
  externally consumed `backend\SeraBackend.exe` and root `Sera.exe` paths.
- Added a packaging regression that rejects reintroduction of `runtime_tmpdir`/one-file specs.

### Validation and boundary

- This change affects Windows packaging and lifecycle behavior only; score generation,
  MusicXML editing, evaluation results and paper metrics are unchanged.
- Packaging regressions passed `3/3`. Both fresh PyInstaller onedir distributions and the
  Electron `release\win-unpacked` application built successfully. The packaged lifecycle smoke
  passed backend health, 120-task/720-run evidence loading, host-scope behavior, compatibility
  launcher shutdown and Electron shutdown; `_MEI*` remained `0` before and after the run.
- The default `run_app.bat` and desktop shortcut icon now target the freshly rebuilt `release`
  package instead of historical `release-dev14-*` packages that still contain one-file backends.

## 2026-08-25 - Phase 39: host-visible dynamic restoration explanation

### Completed

- Investigated the reported red review for `dynamics_009` against the source, Gold output and
  actual Agent runtime output. The Gold and runtime MusicXML files are byte-identical. Their
  canonical diff changes only `s013_m2_rh_3` from `mf` to `f`; pitch, duration and every protected
  event remain unchanged.
- Confirmed the generated runtime file in MuseScore Studio 4.5.2. MuseScore displays `f` on the
  target note and a following `mf` restoration mark. This is required because MusicXML dynamics
  persist until changed; the restoration mark preserves the next event's original effective
  dynamic and is not an additional ScoreDocument event edit.
- Added deterministic host-notation guidance to the review API. For isolated dynamic edits it
  now reports the canonical changed-event count, all MusicXML dynamic marks added/removed and the
  exact restoration event. The review interface presents this separately from event-level diff so
  reviewers do not incorrectly reject a valid task because two host-visible marks represent one
  effective event change.
- Added backend and frontend regressions for `dynamics_009`, rebuilt the canonical Windows desktop
  package and preserved the existing append-only human-review records.

### Validation and delivery evidence

- Passed all 383 project Python tests, all 117 frontend tests in 71 files, the frontend production
  build, deterministic benchmark validation at `120/120`, and the packaged Windows lifecycle
  smoke including frozen review evidence (`120` tasks, `720` runtime runs).
- Browser QA opened the research review, selected `dynamics_009`, rendered the new explanation
  card with one canonical event change and two MuseScore marks, and produced no console warnings
  or errors. Frozen-backend HTTP replay returned the same `f` target and `mf` restoration event.

### Research boundary

- This change improves review correctness and efficiency; it does not change the benchmark Gold
  patch, the actual Agent output or any formal model metric. Human judgement remains independent.

## 2026-08-26 - Phase 40: persistent non-default dynamic round-trip closure

### Completed

- Reproduced the reported Agent proposal on the exact Fixture 13 host shape: MuseScore selection
  M1-M3, two staves and 25 canonical events. The proposal correctly set all selected events to
  `ff`, protected-scope validation passed, but transaction preview returned 23 `E14` errors.
- Isolated all 23 failures to one MusicXML import defect. The exporter correctly collapses a
  persistent dynamic to one visible mark per staff/voice lane, but the importer treated
  note-level `<notations><dynamics>` as local to that note. The first two events re-imported as
  `ff`; the remaining 23 incorrectly fell back to `mf`, causing false round-trip mismatch errors.
- Changed MusicXML import to track persistent dynamic state per staff/voice lane. Staff-wide
  `<direction>` marks remain lane fallbacks, note-level marks override directions at the same
  position, and both forms now persist across later events and measures.
- Added regressions for non-default dynamics on two staves and multiple voices, note-level
  override after a direction mark, and a full-scope `set_dynamic: ff` patch transaction.

### Validation and delivery evidence

- The exact 25-event regression now returns `valid`, zero errors, 25 changed events, zero field
  mismatches and round-trip fidelity `1.0`. The rebuilt frozen backend returns the same result.
- Rendered Browser QA used the same M1-M3 host range and a live DeepSeek patch proposal. The UI
  changed from `不可安全应用` with 23 errors to `验证通过`, kept the 25-event operation and enabled
  transactional apply; browser warnings/errors were empty. No patch was applied to the host.
- Passed all 386 project Python tests, all 117 frontend tests in 71 files, deterministic benchmark
  validation at `120/120`, the 215-module production build and the packaged Windows lifecycle
  smoke. The current frozen backend SHA-256 is
  `62F8F1DF407967FFF246C9E2D43C2706A100A7922175839646429E2F41F4F3D9`.

### Research boundary

- This is a round-trip semantic correctness fix, not a relaxed validator and not evidence of
  model accuracy. `E14` remains a hard error for real notation loss; only the importer state model
  was corrected. Formal experiment outputs and human-review decisions were not rewritten.

## 2026-08-26 - Phase 41: proposal-to-host return and desktop restart closure

### Completed

- Reproduced the reported bridge state in the packaged runtime. Sera had produced a validated
  `insertion_006` proposal, but host revision export rejected its one-note-to-chord replacement
  because every inserted or deleted event was previously treated as unsupported. The bridge
  therefore remained at revision 0 and correctly reported that no reviewed revision existed.
- Extended the source-preserving MusicXML exporter for duration-preserving, same-onset structural
  replacements. It now supports note-to-note and note-to-chord replacements without rebuilding
  the score, while retaining original layout, directions, non-target measures and stable event
  identifiers. Unpaired, duration-changing and rest structural edits still fail closed.
- Added exact `insertion_006` regression coverage. Applying its Gold Patch to `score_006.musicxml`
  creates revision 1 with an eighth-note C4-E4-G4 chord, removes only the replaced target event and
  leaves measure 3 unchanged.
- Fixed a second delivery defect across backend restarts. Electron now tracks the backend PID as
  part of its desktop-session cursor; when the backend PID changes, a newly published session is
  delivered even if its reset sequence number is lower than the previous process's sequence.
- Updated Sera Score Bridge to version 0.3.2. The bridge now distinguishes an in-app draft proposal
  from an applied host revision, uses `Refresh and open applied revision`, and explains the exact
  action required when the current revision is still 0. The installed MuseScore plugin was updated
  with an automatic backup of version 0.3.1.

### Validation and delivery evidence

- Passed all 390 project Python tests and all 117 frontend tests in 71 files. Deterministic
  benchmark validation remains `120/120`; human review remains pending for 120 tasks.
- Rebuilt the Windows Electron package and passed the packaged backend, frontend, legacy launcher,
  Electron lifecycle, frozen review-evidence and host-scope smoke checks.
- Ran a frozen-runtime product workflow on the original `score_006.musicxml`: the proposal validated
  with three additions, one deletion and no protected-scope violation; apply generated revision 1
  using `source_preserving_structural_patch` with no Browser warnings or errors.
- Verified restart recovery against the final packaged backend. With a deliberately stale sequence
  cursor of `999999` and a different prior backend PID, the pending-session endpoint returned the
  newly published `bridge_20260826_051844_eb5dd55a` session and the current backend PID.

### Research boundary

- This closes deterministic delivery and host-export defects; it is not evidence of LLM accuracy
  or compositional quality. The saved `runtime_en.musicxml` files in review workspaces are Agent
  outputs and must not be reused as the source for repeating the same benchmark instruction.
- Arbitrary unmatched insertions/deletions and duration-changing structural rewrites remain
  intentionally unsupported by the source-preserving host exporter until their notation relations
  can be preserved and validated transactionally.

## 2026-08-26 - Phase 42: source-preserving host key-signature export

### Completed

- Reproduced the reported failure after a valid `change_key_signature` proposal. Transaction
  validation succeeded, but host revision generation rejected the global `key` change before
  writing MusicXML, leaving the bridge at revision 0.
- Added source-preserving traditional key-signature export for major/minor keys from seven flats
  through seven sharps. The exporter updates each part's initial `<key><fifths>/<mode>` declaration
  without transposing notes, rebuilding measures, or changing layout and directions.
- Limited the edit to initial attributes before the first timed event. A later mid-measure key
  signature is preserved as a local modulation. Unsupported global fields such as meter continue
  to fail closed instead of triggering a full-score rebuild.
- Added source-preservation metadata for `changed_global_fields` to revision manifests and API
  responses so a global key edit is distinguishable from event changes.

### Validation and delivery evidence

- Added unit regressions for C major to G major source preservation, unchanged pitch sequences,
  preservation of a mid-measure local key change, and continued meter rejection. Added an exact
  `key_001` Gold Patch bridge regression that creates a real revision 1.
- Passed all 394 project Python tests. The rebuilt Windows package passed staged backend, frontend,
  frozen review evidence, host-scope, legacy launcher and Electron lifecycle smoke checks.
- Final frozen-runtime replay `bridge_20260826_060038_a030a2ce` returned `generated`, `valid`,
  committed the transaction, created revision 1 with `source_preserving_global_patch`, wrote
  `fifths=1`, and preserved all 16 source pitches exactly. Frozen backend SHA-256:
  `B62B4CA79E7751BE826B49A12642D14276FAEF717E1621646F194BBFBFFB73CB`.
- Browser QA repeated the visible Chinese workflow from revision 0: selected `修改提案`, generated
  the G-major patch, observed `验证通过`, applied it, and observed `宿主修订已生成` plus revision 1.
  The page had no framework overlay and the Browser console contained no warnings or errors.

### Research boundary

- This is deterministic MusicXML export correctness, not model-quality evidence. It changes the
  host-delivery capability for traditional key signatures but does not add transposition or claim
  support for arbitrary non-traditional key signatures and microtonal key declarations.

## 2026-08-26 - Phase 43: complete benchmark-to-host MusicXML closure

### Completed

- Replaced the previous canonical-only runtime acceptance path with the actual product delivery
  path: source MusicXML import, runtime proposal generation, transaction preview/commit,
  source-preserving MusicXML patch, host-output validation, host-output re-import and deterministic
  constraint evaluation.
- The first real host-export audit exposed 50 hidden failures among 110 executable tasks: all rhythm,
  voice, slur and meter cases. Extended the source-preserving exporter for exact duration notation,
  voice, tie/slur, beam, initial meter and safe structural deletion while preserving original layout,
  directions and unrelated MusicXML.
- Fixed stable event identity during structural deletion and chord-root promotion. Explicitly named
  measures remain narrower than a wider host selection, so `compound_001` with host M2-M3 changes
  only the two intended events in M2.
- Found a second hidden defect after the first 120-task host replay: persistent dynamics contaminated
  protected events in 17 tasks and reduced complete preservation to 0.8583. Dynamic edits now emit
  an exact lane-local target mark and restoration boundary, bringing complete preservation to 1.0.
- Added a frozen-package verifier for `meter_001`. It requires both `change_time_signature` and
  `delete_event`, commits a real revision, re-imports the source-preserving output and checks 3/4,
  19 events and zero constraint errors.

### Validation and delivery evidence

- Exact English/Chinese three-repetition replay: 720/720 runs passed, 660/660 executable source-
  preserving host exports succeeded, 60/60 expected refusals were correct, no unsafe execution,
  MusicXML validity 1.0, constraint satisfaction 1.0 and complete preservation 1.0.
- Widened-host-scope replay: 240/240 passed, 220/220 executable host exports succeeded and all
  174 applicable adjacent-measure expansions retained the instruction-local target.
- Added a benchmark-wide host round-trip regression covering every expected-success Gold output.
  All 110 executable tasks pass; the 10 conflicting/unsupported tasks remain deliberate refusals.
- Passed all 397 Python tests, all 117 frontend tests in 71 files, the 215-module production build,
  120/120 benchmark validation and the full packaged Windows smoke.
- The packaged `meter_001` replay generated revision 1 via `source_preserving_structural_patch`,
  changed only global meter and the six final quarter-note event IDs, and re-imported as 3/4 with
  19 events and zero constraint errors.
- Current packaged hashes: backend
  `770E4CDEDF236988EAD82FF5AD9FD2D14B2D586AB8B40E7F6675C5FFCE9151A0`; desktop
  `FD09C1E98DBEAFA5362D3534DEE2ECBCD45AC2DA7193804EC3C75F8DE9EC087A`.

### Research boundary

- These results prove deterministic product execution and real host-output round trips for the
  frozen benchmark. They are not remote-LLM accuracy, compositional quality or evidence that every
  arbitrary MusicXML edit is supported. Unsafe or structurally ambiguous edits continue to fail
  closed. All 120 musical-quality reviews remain pending and are not auto-filled from these runs.

## 2026-08-26 - Phase 44: desktop host-scope meter proposal regression

### Completed

- Reproduced the user's exact packaged session `bridge_20260826_113757_f1f18ff8`. The local planner
  correctly generated `change_time_signature` plus six `delete_event` targets, but transaction
  preview rejected it with `E05 change_time_signature requires target_scope.whole_score=true`.
- Identified a test/product mismatch: the benchmark and previous packaged verifier supplied an
  already-canonical whole-score scope, while the desktop Agent correctly supplied its real MuseScore
  selection M1-M3. Mixed global/local patches were promoted only when every operation was global.
- Any patch containing a global key or meter operation is now explicitly promoted to whole-score
  authorization. Local changes remain bounded by their event-ID selectors; the meter repair still
  deletes only the six final quarter-note IDs. Requested host scope and promotion provenance remain
  auditable.
- Updated the packaged meter verifier to start from `{measures: [1,2,3]}`, require the promotion,
  require a visible meter diff and six deletions, then commit, source-preserving export and re-import.
- Fixed frozen review evidence selection: the human-review UI now pins the curated 720-run snapshot
  and cannot mix a mutable 120-run development summary with the snapshot's six-run metrics.

### Validation and delivery evidence

- The exact Chinese desktop flow now renders `验证通过`, `删除 6`, `全局 1`, enables apply, and creates
  host revision 1 with no browser warnings/errors.
- The rebuilt frozen package reports `promoted_to_whole_score_for_global_property`, valid preview,
  six deletions, one meter change, revision 1, 3/4, 19 re-imported events and zero constraint errors.
- Passed 399 Python tests, 117 frontend tests, a 215-module production build, a fresh 120/120 runtime
  replay and the complete Windows packaged smoke including frozen 720-run review evidence.

### Research boundary

- The repair aligns real desktop scope with the existing strict global-operation contract; it does
  not weaken selectors, protected-scope validation or transactional rollback. Formal LLM and human
  musical-quality claims remain unchanged.

## 2026-08-26 - Phase 45: reliable desktop session handoff and reactivation

### Completed

- Reproduced the reported Bridge state with `bridge_20260826_124950_a67a831b`: the persisted
  `rhythm_001` session was revision 0 while Sera Desktop still displayed an older `pitch_001`
  session at revision 3. The Bridge message was therefore accurate, but the renderer had missed the
  newer Electron session notification.
- Added a local-backend compensation poll beside Electron IPC. The renderer now receives the latest
  monotonic session even if IPC is delivered before React subscribes or is otherwise dropped.
- Bound every validated proposal to its originating session. Arrival of a newer host session clears
  the old proposal immediately, cancels stale asynchronous results and prevents a transaction from
  exporting to the wrong session.
- Added `POST /integrations/notation-sessions/{session_id}/activate`. MuseScore Bridge 0.3.3 uses it
  when a session has no applied revision, re-focusing Sera on the same persisted session without
  creating a duplicate, applying a draft or changing MusicXML.
- Updated the installed MuseScore plugin with a recoverable backup at
  `SeraBridge.backup_20260826_211329`, preserved the reported session across package replacement and
  restored the canonical launcher path `dist_desktop/release/win-unpacked/Sera.exe`.

### Validation and delivery evidence

- Added regressions for missed renderer IPC, immediate old-proposal invalidation and revision-free
  session reactivation. Passed all 400 Python tests and all 119 frontend tests in 71 files; the
  215-module production build succeeded.
- The canonical frozen backend exposes the activation route. Activating the exact reported session
  returned revision 0 with one source artifact, and rendered desktop QA switched from revision 3 to
  the intended M1-M2/revision-0 workspace without applying a patch.
- Packaged backend SHA-256:
  `152EA6EB57CAD5C3735E4DB955D741766DC0BED041F9187F080A9B92004D95FB`; desktop SHA-256:
  `FD09C1E98DBEAFA5362D3534DEE2ECBCD45AC2DA7193804EC3C75F8DE9EC087A`.

### Research boundary

- This is host-session delivery reliability and safety evidence, not model-quality or task-success
  evidence. Reactivation never approves a proposal; the human must still generate, review and apply
  a validated ScorePatch before a host revision exists.

## 2026-08-26 - Phase 46: MuseScore-safe staff-local voice editing

### Completed

- Reproduced the reported `voice_010` semantic mismatch. The canonical Gold and event diff changed
  only `s017_m3_rh_1` through `s017_m3_rh_4`, but old Sera MusicXML reused voice 1/2 independently
  on both piano staves. MusicXML defines voice identity at part scope, and a real MuseScore export
  confirmed its host convention: staff 1 uses voices 1-4 and staff 2 uses voices 5-8.
- Added a reversible host-boundary mapping. Sera's authoritative ScoreDocument continues to expose
  staff-local voices 1-4, while MusicXML export writes part-wide voice numbers and import maps them
  back to the local lane. Existing MuseScore files in 5-8 form remain stable.
- Source-preserving voice patches now upgrade legacy lower-staff 1/2 tokens before changing a voice.
  This prevents the new staff-1 voice from being interpreted as the existing staff-2 logical voice;
  the normalization is reported separately and does not count as a canonical protected-scope edit.
- Refreshed 20 derived source MusicXML files and 110 expected-output MusicXML files from unchanged
  canonical JSON. Task instructions, Gold patches, constraints, event diffs and human reviews were
  not rewritten.
- Updated frozen review evidence to `softwarex_runtime_acceptance_720_v4` and widened-scope evidence
  to `softwarex_host_scope_robustness_240_v3`, so reviewers no longer open stale host outputs.

### Validation and delivery evidence

- `voice_010` now has raw host lanes M1/M2 `{staff 1: voice 1, staff 2: voice 5}` and M3
  `{staff 1: voice 2, staff 2: voice 5}`. Its canonical diff remains exactly four voice-only changes.
- The denser `voice_004` case retains staff-2 voices 5 and 6 in all three measures; only staff-1
  measure 3 changes from voice 1 to 2.
- Core benchmark validation passed 120/120. Exact bilingual three-repetition product replay passed
  720/720 with 660/660 source-preserving exports; widened host-scope replay passed 240/240 with
  220/220 exports. Both report zero failures and complete preservation 1.0.
- Added regressions for MusicXML 1/2 versus 5/6 encoding, local-voice re-import, legacy-token upgrade
  and protected lower-staff semantics. All 402 Python tests pass; draft SoftwareX package verification
  passes with 1,380 exact-run and 460 scope-run evidence files hashed.
- Rebuilt the Windows desktop package and passed the packaged smoke, including real HTTP preview,
  apply, export and re-import checks for both `voice_010` and dense `voice_004`. The final targeted
  regression set passes 31/31. Release SHA-256 values are
  `FD09C1E98DBEAFA5362D3534DEE2ECBCD45AC2DA7193804EC3C75F8DE9EC087A` for `Sera.exe` and
  `6B015A532B30F3BA7DB7E97A1799E253321F1A7A604A2D667C397B4D9FA2E24F` for `SeraBackend.exe`.

### Research boundary

- The replay is deterministic product-path evidence and does not establish remote-LLM accuracy or
  subjective musical quality. A final visual check in the user's MuseScore 4.5.2 remains part of the
  human review protocol; Sera now provides the host-compatible artifact for that check.

## 2026-08-27 - Phase 47: frozen human-review evidence and SoftwareX release surface

### Completed

- Verified the completed desktop review state through the running API: 120/120 primary reviews,
  30/30 stratified repeat checks, zero stale records, zero remaining tasks, and every category
  complete. Exported 194 append-only audit records to the immutable
  `softwarex_human_review_120_v1` publication snapshot with per-file SHA-256 hashes.
- Added a fail-closed human-evidence exporter and strict SoftwareX package validation. Incomplete
  counts, JSON/CSV disagreement, stale records, or hash drift now fail package verification.
- Kept the benchmark audit implementation in source while hiding it from the ordinary Agent build.
  It is available only when a research build explicitly sets
  `VITE_SERA_ENABLE_RESEARCH_REVIEW=true`.
- Updated the SoftwareX manuscript and release documents to state the actual review result and its
  limitation: the same pseudonymous reviewer performed both passes, so no independent inter-rater
  or universal aesthetic-quality claim is made.

### Validation

- 404/404 Python tests and 120/120 frontend tests in 72 files pass.
- The production frontend build succeeds with 216 transformed modules.
- Human evidence unit tests and the default-hidden review-mode regression pass.
- The final packaged Windows build passes backend, launcher and Electron runtime smoke,
  including frozen 120-task evidence plus `compound_001`, `meter_001`, `voice_010` and
  `voice_004` source-preserving MusicXML round trips.
- Deterministic SoftwareX archives pass CRC/sensitive-file inspection; their final
  SHA-256 values are written to the external release manifest.

### Remaining author-controlled work

- Confirm author/affiliation/support/funding/CRediT/legal fields, approve the MIT owner statement,
  inspect and commit the release, publish an immutable tag, mint the archive DOI, and complete the
  final official-template/Editorial Manager submission. These actions are intentionally not
  automated because they require identity, legal authority, or external publication.

## 2026-08-27 - Phase 48: SoftwareX reviewer reproducibility closure

### Completed

- Added an offline six-task reviewer demo that uses the product runtime generator,
  transaction, protected-scope validation and source-preserving host MusicXML round trip.
  All six tasks pass; five executable cases produce MusicXML and one conflict refuses safely.
- Added Windows research CI, tested direct-dependency constraints, a reviewer guide and a
  minimum Python-only installation path. Corrected the previously invalid documented npm
  prefix ordering and protected it with a regression test.
- Kept benchmark task metadata immutable while resolving the misleading review summary:
  automatic core validation now shows zero effective human reviews pending and separately
  reports the 120 original metadata flags plus the complete 120+30 frozen review evidence.
- Added a compact manuscript evidence/claim-boundary table, rebuilt the DOCX, and compiled
  an eight-page SoftwareX PDF with Tectonic. All PDF pages were visually inspected and
  contain readable tables, figure, line numbers and references.

### Validation and research boundary

- 408/408 Python tests, 120/120 frontend tests, the 216-module build, 120/120 benchmark
  validation, 6/6 reviewer demo and draft SoftwareX audit pass.
- This phase increases installation and review reproducibility. It does not claim live-LLM
  accuracy, inter-rater reliability or musical/aesthetic quality.
