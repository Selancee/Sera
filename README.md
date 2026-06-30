# Sera

Sera is an agent-assisted prompt-to-score music generation prototype. V0.5 keeps the V0.4/V0.2 runnable path, but fixes the "small model generates monotonous quarter-note MusicXML" problem by moving the model to local musical tasks: melody fragments, motif variation, cadence generation, and rhythm rewrite. The Agent plans structure, the rule-based generator preserves MusicXML legality, and postprocess/metrics check musicality collapse modes.

## Pipeline

User Prompt -> Prompt Understanding Agent -> Structured Music Intent -> Composition Planning Agent -> Measure-level Music Plan JSON -> Symbolic Music Generator -> Draft MusicXML / MIDI / ABC -> Music Rule Validator -> Revision Agent -> Final Score -> App Preview / Playback / Export.

## Project Layout

- `backend/`: FastAPI app, mock/LLM-ready agents, symbolic generator, validators, exporters, experiment logging.
- `frontend/`: React + Vite research workbench.
- `evaluation/`: batch prompt evaluation, metrics, and human evaluation form.
- `training/`: cloud-GPU-friendly symbolic dataset, tokenizer, trainer stub, and model evaluator.
- `papers/`: paper outline, experiment plan, system description, figure plan, and figures.
- `examples/`: seed prompts and compatibility exports.
- `experiments/`: one independent folder per generation run.

## Quick Start

Recommended on Windows:

```powershell
D:\Sera\run_app.bat
```

This one-click launcher starts or reuses the backend and frontend, opens the browser, and writes logs to `data/metadata`.
It also starts the backend in model-priority mode and points symbolic inference at
`D:\Sera\models\sera_symbolic_small` when no custom model environment variable is set.

If the browser opens to a blank page, close the page and run `D:\Sera\run_app.bat` again. The launcher checks that the backend exposes the V0.2 API and refreshes stale local Sera frontend processes before opening `http://127.0.0.1:5173`.

Optional desktop shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\create_desktop_shortcut.ps1
```

Stop Sera processes started by the launcher:

```powershell
D:\Sera\stop_app.bat
```

Advanced manual startup:

```powershell
cd D:\Sera
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```powershell
cd D:\Sera\frontend
npm install
npm run dev
```

Open:

- Frontend app: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000/docs`

## API

- `POST /generate`: prompt to plan, score, validation, evaluation, and artifacts.
- `POST /revise`: revise an existing run with user feedback.
- `POST /rate`: save local human evaluation ratings for a run.
- `GET /model/status`: inspect the optional trained symbolic model and latest AutoDL run metrics.
- `GET /model/registry`: list local `models/<model_name>` folders selectable by the app.
- `POST /model/select`: switch the active symbolic model for subsequent main-page generation.
- `POST /model/sample`: generate or replay token-level symbolic model samples for the frontend Model Lab.
- `GET /export/{run_id}/{format}`: download `musicxml`, `midi`, `abc`, `pdf`, `plan`, `validation_report`, or `experiment_log`.
- `POST /evaluate`: return saved metrics for one run.
- `GET /experiments`: list recent experiment logs.

## Experiment Outputs

Each generation writes:

```text
experiments/<timestamp_prompt_hash>/
  prompt.txt
  plan.json
  generated.musicxml
  generated.mid
  generated.pdf
  validation_report.json
  revision_history.json
  human_rating.json
  metadata.json
  experiment_log.json
```

The validator checks XML parsing, `music21` parsing when available, plan/measure count match, per-staff/per-voice bar completeness, instrument pitch range, empty measures, MIDI export, and PDF export.

## LLM Provider

Sera runs in mock mode by default. A live OpenAI-compatible provider can be enabled without hardcoding credentials:

```powershell
$env:SERA_LLM_PROVIDER = "openai"
$env:SERA_LLM_MODEL = "gpt-4.1-mini"
$env:SERA_LLM_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_API_KEY = "<set outside source control>"
```

See `.env.example` for local environment variables.

## V0.5 Diagnostics

```powershell
python -m evaluation.analysis.dataset_diagnostics --input_dir data --output_dir evaluation/results
python -m evaluation.analysis.generated_music_diagnostics --input_dir examples/scores --output_dir evaluation/results
```

Outputs include `dataset_diagnostics.json`, `generated_music_diagnostics.json`, `rhythm_distribution.csv`, and `pitch_interval_distribution.csv`.

## V0.5 Data And Training

Build augmented data without overwriting originals:

```powershell
python -m training.augmentation.build_augmented_dataset --input_dir examples/scores --output_dir data/augmented --fragment
python -m training.tasks.build_multitask_dataset --input_dirs data/fragments data/augmented examples/scores --output data/tokenized_v05/multitask_dataset.jsonl
```

Smoke-check V0.5 training:

```powershell
python training/train_symbolic_model.py --config training/configs/sera_v05_smoke.yaml --dry-run
```

Full small config:

```powershell
python training/train_symbolic_model.py --config training/configs/sera_v05_small.yaml --out models/sera_v05_small
```

## V0.5 Hybrid Generation

The frontend now exposes `generator_mode` with `rule_based`, `model_based`, `hybrid_v04`, and `hybrid_v05`. The API can also select it directly:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/generate `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"prompt":"Compose an 8 bar C major melody with varied rhythm.","generator_mode":"hybrid_v05"}'
```

`hybrid_v05` records `model_task_type`, `generated_fragment`, `decoding`, `postprocess_report`, `fallback_reason`, `final_validation_report`, and musicality metrics in the experiment log.

## V0.4 Vs V0.5 Experiment

```powershell
python evaluation/run_v05_musicality_eval.py --max-prompts 3
```

Full run writes `evaluation/results/v05_musicality_results.csv`, `v05_musicality_summary.json`, `v05_ablation_table.tex`, and plots under `evaluation/results/v05_musicality_plots/`.

## Evaluation

```powershell
python evaluation/run_evaluation.py --prompts examples/prompts/seed_prompts.jsonl
```

Outputs:

- `evaluation/evaluation_results.csv`
- `evaluation/evaluation_summary.json`

Metrics: `musicxml_validity_rate`, `midi_export_success_rate`, `pdf_export_success_rate`, `bar_completeness_score`, `pitch_range_validity_rate`, `empty_measure_rate`, `prompt_adherence_rule_score`, `revision_success_rate`, `human_rating_present`, `human_average_score`, `rhythmic_diversity_score`, `quarter_note_dominance_score`, `melodic_interval_variety_score`, `cadence_presence_score`, and `overall_musicality_proxy_score`.

## Training Pipeline

```powershell
python training/build_dataset.py --sources examples/scores
python training/tokenize_musicxml.py
python training/train_symbolic_model.py --dry-run
python training/evaluate_model.py
```

Cloud training on AutoDL:

```bash
bash training/autodl_train.sh
```

By default the AutoDL script trains a compact native PyTorch decoder-only Transformer on Sera generated examples plus the ASAP GitHub MusicXML dataset. It keeps third-party data and checkpoints under `/root/autodl-tmp` instead of committing them.

Budget-capped 50 RMB verification:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\run_autodl_50rmb_training.ps1 `
  -SshTarget root@<autodl-host> `
  -Port <ssh-port> `
  -MaxRunHours 20 `
  -MaxExamples 1200 `
  -Epochs 6
```

That script saves the checkpoint in both `/root/autodl-tmp/sera_runs/<run_id>` and `/root/autodl-tmp/sera_models/<run_id>`, writes `sha256_manifest.txt`, and creates `/root/autodl-tmp/sera_models/<run_id>.tar.gz`.

The training scripts are ready for local MusicXML/PDMX/MetaScore-derived folders and future POP909/Lakh MIDI Dataset conversions. They do not download large datasets locally.

## Symbolic Model Lab

The frontend has a `Model` tab for qualitative testing of the trained symbolic model. By default it reads lightweight
AutoDL evidence from `docs/training_runs/<run_id>/samples.json` and `training_metrics.json`.

For live checkpoint inference, copy the AutoDL checkpoint artifacts outside Git into the default local model folder:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\fetch_autodl_model.ps1 `
  -SshTarget root@<autodl-host> `
  -Port <ssh-port> `
  -RemoteRunDir /root/autodl-tmp/sera_models/<run_id> `
  -ModelName sera_v05_50rmb

powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\verify_model_artifacts.ps1 `
  -ModelDir D:\Sera\models\sera_v05_50rmb
```

The script downloads `model.pt`, `vocab.json`, audit files, and `sha256_manifest.txt`, verifies hashes when the manifest exists, updates local `.env`, and leaves the large files ignored by Git.

Manual equivalent:

```powershell
$env:SERA_SYMBOLIC_MODEL_DIR = "D:\Sera\models\sera_symbolic_small"
$env:SERA_GENERATOR_BACKEND = "model"
# Expected files:
# D:\Sera\models\sera_symbolic_small\model.pt
# D:\Sera\models\sera_symbolic_small\vocab.json
```

Then start the backend and frontend. The `Model` tab will switch from `recorded_sample` to `checkpoint` mode when
`model.pt` is found and PyTorch is installed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
D:\Sera\stop_app.bat
D:\Sera\run_app.bat
Invoke-RestMethod http://127.0.0.1:8000/model/status
```

The backend now uses `SERA_GENERATOR_BACKEND=model` by default in the launcher. The main `/generate` route is
model-conditioned: it calls the active checkpoint first, extracts pitch/duration hints from the model tokens, and then
uses Sera's safe MusicXML assembler to produce valid MusicXML, MIDI, and PDF. The experiment log records this as
`generator_mode: model_conditioned` with `metadata.symbolic_model.loaded: true`.

The `Model` tab also exposes the local model registry. Put future checkpoints under `models/<model_name>/model.pt`,
refresh the backend, and select that model from the UI to use it for later main-page generation. UI selection persists
the active model to `.env` while preserving unrelated keys such as `OPENAI_API_KEY`. The same switch is available through
the API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/model/registry
Invoke-RestMethod http://127.0.0.1:8000/model/select `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"model_name":"sera_symbolic_small","persist":true}'
```

Future larger checkpoints can also be called without code changes by setting environment variables directly:

```powershell
$env:SERA_ACTIVE_SYMBOLIC_MODEL = "sera_symbolic_large"
$env:SERA_SYMBOLIC_MODEL_DIR = "D:\Sera\models\sera_symbolic_large"
$env:SERA_GENERATOR_BACKEND = "model"
D:\Sera\stop_app.bat
D:\Sera\run_app.bat
```

V0.5 deliberately does not ask the small model to generate complete MusicXML from scratch. The current dataset is too small and token frequencies collapse toward common XML and quarter-note patterns. Local tasks give the model a narrower objective while Sera's rules keep notation valid.

## V0.6 Score Workbench

V0.6 adds an independent Score Workbench beside the existing Generate flow. The workbench edits a canonical `ScoreDocument` JSON model instead of editing raw MusicXML text directly. MusicXML is now an import/export format for the workbench, while all user and Agent edits are represented as `ScoreOperation` objects with undo/redo snapshots.

Run the app as usual and open the `Workbench` tab:

```powershell
D:\Sera\run_app.bat
```

Workbench capabilities now include:

- Import generated or external MusicXML into `ScoreDocument`.
- Click measures and notes in the SVG workbench canvas.
- Edit pitch, duration, dynamic, staff, key, meter, tempo, harmony, section, and cadence labels.
- Insert notes/rests from palettes.
- Undo and redo operation history.
- Ask the mock-safe Score Editing Agent for a local `ScorePatch`.
- Preview, accept, reject, or regenerate patches.
- Export edited scores to MusicXML, MIDI, and PDF.
- Save/open `.sera.json` workbench project files.

Backend workbench APIs are available in Swagger:

```text
POST /score/import_musicxml
POST /score/export_musicxml
POST /score/export_midi
POST /score/export_pdf
POST /score/validate
POST /score/apply_operation
POST /score/undo
POST /score/redo
POST /score/agent_edit
POST /score/preview_patch
POST /score/apply_patch
POST /score/reject_patch
POST /score/save_project
POST /score/load_project
```

Score editing evaluation:

```powershell
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.score_editing.summarize_edit_results
```

Outputs are written to `evaluation/results/score_editing_results.csv`, `score_editing_summary.json`, and `score_editing_table.tex`.

## V0.7 Score Workbench

V0.7 keeps the V0.6 canonical `ScoreDocument` and operation model, then adds renderer adapters, stricter patch validation, partial patch application, explain-only Agent analysis, and frontend automated tests.

Workbench renderer modes:

- `auto`: try OpenSheetMusicDisplay first, then fall back to SVG.
- `osmd`: request OpenSheetMusicDisplay explicitly; failures are shown in the status bar and editing falls back to SVG.
- `vexflow`: reserved adapter placeholder; currently falls back to SVG.
- `fallback`: always use the built-in SVG renderer.

Use the renderer selector in the Score Workbench toolbar. Backend-visible capability checks are available at:

```text
GET /score/render_capabilities
GET /score/workbench_health
```

LLM score editing is mock-safe by default:

```powershell
$env:SERA_LLM_PROVIDER = "mock"
```

Live OpenAI-compatible providers can be enabled without changing code:

```powershell
$env:SERA_LLM_PROVIDER = "openai"   # or deepseek, qwen
$env:SERA_LLM_MODEL = "gpt-4.1-mini"
$env:SERA_LLM_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_API_KEY = "<set outside source control>"
```

If the provider is missing, the key is absent, JSON is invalid, schema validation fails, or repair fails, Sera falls back to the deterministic mock patch planner.

New workbench APIs:

```text
POST /score/validate_patch
POST /score/partial_apply_patch
POST /score/explain_selection
GET /score/render_capabilities
GET /score/workbench_health
```

Patch workflow:

1. Select one or more measures in Workbench.
2. Choose preserve constraints, target difficulty, patch size, staff, and voice in Agent Tools.
3. Click `Preview Agent Patch`.
4. Review diff counts, prompt-alignment scores, validation recommendation, and over-editing risk.
5. Use `Accept all`, `Reject`, `Regenerate patch`, or operation-level partial apply.

Explain selected passage:

1. Select a measure range.
2. Click `Explain` or the `Explain selected passage` Agent tool.
3. Sera returns harmony, melodic, rhythmic, difficulty, and suggested-edit notes without modifying the score.

V0.7 score editing evaluation:

```powershell
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.score_editing.summarize_edit_results
```

Outputs are written to `evaluation/results/score_editing_v07_results.csv`, `score_editing_v07_summary.json`, `score_editing_v07_table.tex`, and `score_editing_v07_failure_cases.json`.

Current non-goals remain MuseScore-level engraving and full notation editing: precise drag-to-pitch editing, advanced slurs, pedal marks, lyrics, fingering, complex tuplets, and real-time collaboration are still V0.8+ work.

## Tests

```powershell
python -m pytest
cd frontend
npm run build
npm test
```

Recommended full V0.7 verification:

```powershell
python -m pytest -q
cd frontend
npm run build
npm test
cd ..
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.score_editing.summarize_edit_results
```

## V0.8 Score Workbench

V0.8 turns the Workbench into a MuseScore-like editing core while keeping the V0.7 fallback path. The Workbench now supports Select Mode, Note Input Mode, duration and accidental controls, tie/slur actions, staff and voice selection, note-level overlay hit testing, vertical drag pitch editing, fake playback scrubber, autosave recovery, `.sera.json` project migration, left-hand accompaniment generation, and Agent edits that receive recent manual-edit context.

Renderer modes remain fallback-safe:

- `auto`: try OSMD and fall back to SVG.
- `osmd`: force OpenSheetMusicDisplay and report fallback reason on failure.
- `vexflow`: reserved adapter path with safe fallback.
- `fallback`: deterministic SVG renderer and overlay hit map.

Manual editing basics:

- Click notes/rests/measures in Select Mode; Shift-click or marquee-select for larger selections.
- Use Note Input Mode plus `A-G`, `R`, `1/2/4/8/6`, `.`, arrows, `Delete`, `Ctrl+Z`, `Ctrl+Y`, `Space`, `Esc`, and `Ctrl+A`.
- Drag selected notes vertically to change pitch; horizontal movement is quantized in the fallback editor.
- Generate simple left-hand accompaniment from the selected range.

Agent editing now sends `current_selection`, `recent_operations`, `dirty_measures`, validation warnings, playback position, selected-note summary, inferred user edit intent, and a preserve timestamp. Mock and LLM modes can protect recent manual notes through `exclude_event_ids`.

New V0.8 APIs:

- `POST /score/operation`
- `POST /score/batch_operations`
- `POST /score/light_validate`
- `POST /score/full_validate`
- `POST /score/render_preview_musicxml`
- `POST /score/generate_accompaniment`
- `POST /score/migrate_project`
- `POST /score/export_project_package`
- `POST /score/revert_last_agent_patch`
- `POST /score/continue_from_last_edit`

V0.8 verification:

```powershell
python -m pytest -q
cd D:\Sera\frontend
npm.cmd run build
npm.cmd test
cd D:\Sera
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.score_editing.summarize_edit_results
python -m evaluation.workbench_editing.run_workbench_edit_eval --max-prompts 3
python -m evaluation.workbench_editing.summarize_workbench_edit_results
```

V0.8 benchmark outputs are `evaluation/results/workbench_editing_v08_results.csv`, `workbench_editing_v08_summary.json`, `workbench_editing_v08_table.tex`, and `workbench_editing_v08_failure_cases.json`.

Still out of scope: full MuseScore-grade engraving, advanced tuplets/ornaments/pedal/lyrics/fingering, exact OSMD internal notehead binding in all browsers, real audio-synchronized MIDI playback, full layout reflow, and multi-user collaboration.

## TODO

1. Add OpenSheetMusicDisplay or Verovio for full browser engraving.
2. Add MuseScore CLI detection UX and production PDF rendering.
3. Replace heuristic prompt parsing with a provider registry and stricter schema-constrained LLM calls.
4. Train and evaluate a real V0.5 checkpoint on larger structured-event fragments.
5. Add multi-rater participant/session support for formal human-subject studies.
6. Improve postprocess so it preserves richer two-staff accompaniment after structured-event repair.
7. Improve OSMD note-level hit mapping beyond stable measure-level overlay selection.
8. Add precise drag-to-pitch editing, advanced articulations, slurs, pedal marks, lyrics, and collaboration support.
9. Compare mock, OpenAI, DeepSeek, and Qwen score-editing patches on the V0.7 benchmark.
10. Build V0.8 real-time playback scrubbing and richer MuseScore-like notation editing.
