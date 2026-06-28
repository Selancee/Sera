# Sera

Sera is an agent-assisted prompt-to-score music generation prototype. V0.2 turns a natural-language prompt into a schema-validated Agent plan, a measure-level composition plan, MusicXML, MIDI, ABC, PDF, validation report, revision history, and reproducible experiment logs.

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

## Evaluation

```powershell
python evaluation/run_evaluation.py --prompts examples/prompts/seed_prompts.jsonl
```

Outputs:

- `evaluation/evaluation_results.csv`
- `evaluation/evaluation_summary.json`

Metrics: `musicxml_validity_rate`, `midi_export_success_rate`, `pdf_export_success_rate`, `bar_completeness_score`, `pitch_range_validity_rate`, `empty_measure_rate`, `prompt_adherence_rule_score`, `revision_success_rate`, `human_rating_present`, and `human_average_score`.

## Training Pipeline

```powershell
python training/build_dataset.py --sources examples/scores
python training/tokenize_musicxml.py
python training/train_symbolic_model.py --dry-run
python training/evaluate_model.py
```

The training scripts are pipeline scaffolds for local MusicXML/PDMX/MetaScore-derived folders and future POP909/Lakh MIDI Dataset conversions. They do not download large datasets or run heavy training locally.

## Tests

```powershell
python -m pytest
cd frontend
npm run build
```

## TODO

1. Add OpenSheetMusicDisplay or Verovio for full browser engraving.
2. Add MuseScore CLI detection UX and production PDF rendering.
3. Replace heuristic prompt parsing with a provider registry and stricter schema-constrained LLM calls.
4. Implement a neural symbolic event vocabulary and LoRA training loop.
5. Add multi-rater participant/session support for formal human-subject studies.
