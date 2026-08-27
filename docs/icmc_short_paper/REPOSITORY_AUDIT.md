# SeraEdit Repository Audit

Audit date: 2026-08-05  
Repository: `D:\Sera` (local development checkout)  
Baseline commit: `b4eb139`  
Scope: reliable, local MusicXML editing through structured and validated patches.

## 1. Current architecture

- Backend: FastAPI with dependency-light Python domain dictionaries, Pydantic request models, pytest, and JSON schema artifacts.
- Frontend: React 18, Vite, Vitest, OpenSheetMusicDisplay, and VexFlow. The Workbench is also packaged in an Electron desktop shell.
- Canonical state: `backend/services/score_document_service.py` defines ScoreDocument construction, normalization, MusicXML import/export, MIDI note-event conversion, and stable `sera-event-id` export markers.
- Editing: `backend/services/score_operation_service.py` applies auditable ScoreOperation objects and stores before/after snapshots for undo/redo.
- Patch workflow: `ScorePatchService` supports preview, validation, full apply, partial apply, and reject. `ScorePatchValidationService` performs the current V0.7 range and MusicXML checks.
- Notation validation: `backend/notation` contains notation normalization, duration math, beam/rest grouping, and validation. `backend/validation/musicxml_validator.py` performs XML/MusicXML checks and optional music21 parsing.
- Agent/provider path: `backend/agents/score_editing_agent.py` calls the OpenAI-compatible provider factory and falls back to deterministic mock editing when no API key exists. OpenAI, DeepSeek, and Qwen endpoints are represented by `backend/llm/provider_factory.py`.
- API: the repository already exposes import/export, preview/apply/partial/reject patch, light/full validation, batch operations, undo/redo, agent patch revert, project persistence, render adapters, and notation-host bridge endpoints.
- Persistence: editable projects are local `.sera.json` packages under `data/projects`; experiment records are append-only JSONL plus per-run directories.

## 2. Directly reusable modules

| Contract need | Existing implementation | Reuse decision |
| --- | --- | --- |
| Canonical ScoreDocument | `backend/services/score_document_service.py` | Reuse as authority; research modules operate on deep copies. |
| Stable event IDs | MusicXML `sera-event-id` comments/technical notation | Reuse and add round-trip regression coverage. |
| ScoreOperation apply | `backend/services/score_operation_service.py` | Reuse through an explicit SeraEdit operation adapter. |
| Patch preview/apply/reject | `backend/services/score_patch_service.py` | Preserve for product compatibility; add a strict research transaction layer. |
| Undo/redo | operation snapshots and `/score/undo`, `/score/redo` | Reuse semantics; add transaction-level history. |
| MusicXML validation | `MusicXMLValidator` and import/export functions | Reuse for final round-trip validation. |
| Light/full validation | `/score/light_validate`, `/score/full_validate` | Reuse as product endpoints; research validators emit a separate stable report. |
| Batch operations | `/score/batch_operations` | Reuse for existing UI; strict research `batch` expands transactionally. |
| LLM adapters | `backend/llm` | Wrap without changing existing agent behavior. |
| Rendering | backend render service, OSMD, VexFlow fallback | Reuse later for benchmark review/demo. |
| Evaluation framework | `evaluation/*`, experiment logger | Reuse conventions; add isolated SeraEdit conditions/runners. |

## 3. Missing research components

1. A versioned paper-facing ScorePatch schema with target scope, protected scope, source fingerprint, operation preconditions, expected effects, and provenance.
2. Deterministic ScoreScope matching across measure, part, staff, voice, event, time range, and exclusions.
3. Canonical fingerprints that exclude volatile timestamps but detect semantic score drift.
4. Protected-scope comparison of pre/post score states, including implicit protection outside the target scope.
5. A transaction coordinator that validates, clones, applies, round-trips, commits, or rolls back atomically.
6. A benchmark/task schema, generated source scores, gold patches, deterministic constraints, and validation tooling.
7. Fairly separated Full Rewrite, Patch Only, and Sera Full experimental conditions.
8. Provider response metadata for token use, request IDs, cost estimates, finish reasons, and raw response preservation.
9. Resumable experiment manifests and automatic paper statistics/assets.

## 4. Technical debt

- ScoreDocument event offsets are stored as floats even though notation helpers often convert through `Fraction(str(value))`. SeraEdit must use rational comparisons at validation boundaries without rewriting the product schema in this batch.
- Imported event IDs are currently regenerated from measure/order; exported `sera-event-id` markers are written, but import does not yet reliably restore every marker.
- The current V0.7 ScorePatch schema is deliberately loose and has no protected scope or source fingerprint.
- Existing unknown ScoreOperation types may become no-ops. The research adapter must reject unsupported operations instead of silently succeeding.
- ScoreDocument is piano-oriented and flattens part identity into staff labels; multi-part benchmark claims must wait for a richer canonical importer.
- The legacy generation UI remains in the repository. The Workbench is authoritative for editing, but regression tests must prevent preview/playback/export from diverging from ScoreDocument.

## 5. Short-paper risks

- Mock-provider runs are engineering smoke evidence only and cannot be reported as model effectiveness.
- No 120-task reviewed benchmark exists yet; Batch 1 must be validated before scaling.
- MusicXML coverage is intentionally incomplete for tuplets, grace notes, beams, and complex cross-voice relations.
- Provider/model prices and versions are time-dependent and must remain configuration data.
- Real MuseScore/Sibelius round-trip behavior is not established by internal MusicXML tests alone.
- The dirty worktree contains prior user work; all SeraEdit changes must remain additive and independently testable.

## 6. Planned additions

- `sera_edit/domain`, `sera_edit/validation`, `sera_edit/execution`, `sera_edit/providers`, `sera_edit/generation`, and `sera_edit/api`.
- `benchmark/schemas`, `benchmark/source_scores`, `benchmark/tasks`, `benchmark/gold_patches`, `benchmark/splits`, and validation/generation tools.
- `evaluation/conditions`, `evaluation/runners`, `evaluation/configs`, and deterministic metric modules.
- `docs/icmc_short_paper`, `paper`, `demo`, and reproducibility scripts in later phases.

## 7. Compatibility strategy

- Do not replace existing ScorePatch endpoints or schema in the first research phase.
- Convert strict SeraEdit operations to existing ScoreOperation calls only after strict validation.
- Never mutate caller-owned ScoreDocument objects; commit returns a new canonical document.
- Keep all benchmark and experiment artifacts under new namespaces.
- Add product API integration only after the strict core and benchmark tests pass.
- Preserve existing generation, playback, export, desktop, and notation-host workflows.

## Regression baseline

Executed on 2026-08-05 before SeraEdit changes:

- `D:\Sera\.venv\Scripts\python.exe -m pytest -q`: 193 passed, 0 failed.
- `npm.cmd test -- --run` in `frontend`: 65 files / 90 tests passed, 0 failed.
- `npm.cmd run build` in `frontend`: passed; Vite reported only existing large-chunk warnings.

The RuntimeErrorBoundary test intentionally logs a generated render exception while still passing.
# Composer V0.1 compatibility addendum (2026-08-06)

- `ScoreDocument`, stable event IDs, source fingerprints, ScoreScope, PatchTransaction, protected-scope validation, MusicXML round-trip validation, and source-preserving host export are reused without replacement.
- New creative work lives under `sera_edit/composer`; legacy generation code is not made authoritative and the host remains the notation source of truth.
- The executable V0.1 operation surface is intentionally narrower than the internal ScorePatch schema: Composer emits only `set_pitch`, because this is the structural boundary already proven to preserve imported host MusicXML.
- LLM output is a typed high-level plan, never a final score. Server canonicalization prevents model output from changing key, meter, selected measures, source fingerprint, preservation flags, or event IDs.
- Orchestration changes are represented as plan-only advice until the bridge has a host-tested instrument/part mutation and one-step undo contract.
