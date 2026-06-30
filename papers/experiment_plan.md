# Sera Experiment Plan

## Research Questions

1. Does structured Agent planning improve prompt adherence and score validity compared with direct symbolic baseline generation?
2. Does validator-guided revision improve MusicXML validity, bar completeness, and pitch range compliance?
3. Are generated scores readable and editable enough for early-stage composition workflows?

## Prompt Set

Use `examples/prompts/seed_prompts.jsonl`, currently 20 prompts covering:

- Classical piano.
- Romantic piano.
- Jazz.
- Pop ballad.
- Chinese pentatonic style.
- Electronic ambient.
- Children's beginner piano.
- Complex triple meter.
- Fast lively style.
- Sad adagio style.

## Automatic Evaluation

Run:

```powershell
python evaluation/run_evaluation.py --prompts examples/prompts/seed_prompts.jsonl
```

Outputs:

- `evaluation/evaluation_results.csv`
- `evaluation/evaluation_summary.json`

Metrics:

- `musicxml_validity_rate`
- `midi_export_success_rate`
- `pdf_export_success_rate`
- `bar_completeness_score`
- `pitch_range_validity_rate`
- `empty_measure_rate`
- `prompt_adherence_rule_score`
- `revision_success_rate`
- `human_rating_present`
- `human_average_score`

## Human Evaluation

Use `evaluation/human_eval_form.md` to collect 1-5 ratings:

- Prompt adherence.
- Musical coherence.
- Notation readability.
- Playability.
- Editability.
- Preference between first draft and revised version.

The V0.2 app also includes a Human Evaluation panel that writes these ratings
to `experiments/<run_id>/human_rating.json` and the append-only experiment log.

## Baselines

- `rule_based_v0_2`: current deterministic Agent plan plus symbolic generator.
- `v04_model_based`: old model-conditioned path that attempts broad MusicXML-style generation.
- `v04_rule_based`: deterministic legal MusicXML baseline.
- `v05_model_fragment`: local task fragment generation without postprocess.
- `v05_hybrid`: Agent + rule legality + local model fragments + postprocess.
- `v05_hybrid_without_postprocess`: ablation removing postprocess repair.
- TODO: direct LLM-to-MusicXML baseline.
- TODO: trained symbolic Transformer baseline using local MusicXML/PDMX/MetaScore/POP909/Lakh-derived data.

## V0.4 vs V0.5 Musicality Ablation

Run:

```powershell
python evaluation/run_v05_musicality_eval.py
```

Primary metrics:

- MusicXML validity rate.
- MIDI export success rate.
- Rhythmic diversity score.
- Quarter-note dominance score.
- Melodic interval variety score.
- Stepwise overuse penalty.
- Cadence presence score.
- Overall musicality proxy score.
- Average generation time.

## V0.6 Score Editing Evaluation

Run:

```powershell
python -m evaluation.score_editing.run_score_edit_eval
python -m evaluation.score_editing.summarize_edit_results
```

Prompt categories:

- Make selected measures more lyrical.
- Simplify left hand or reduce difficulty.
- Add a clearer cadence.
- Increase rhythmic density.
- Preserve melody while rewriting accompaniment.
- Preserve harmony while changing melodic expression.
- Add waltz-like or pentatonic local color.

Primary metrics:

- Patch validity rate.
- Patch application success rate.
- MusicXML valid after edit rate.
- Constraint respect score.
- Selection respect score.
- Prompt alignment edit score.
- Validation warning reduction.
- Average patch size.
- Undo/redo success rate.
- User acceptance proxy score.

## V0.7 Score Editing Benchmark

Run:

```powershell
python -m evaluation.score_editing.run_score_edit_eval --max-prompts 3
python -m evaluation.score_editing.summarize_edit_results
```

The V0.7 prompt set contains 50 edit instructions covering local melody rewriting, left-hand accompaniment rewriting, rhythmic density increase/decrease, preserve-melody and preserve-harmony constraints, cadence insertion, difficulty changes, pentatonic color, triple-meter requests, warning repair, explain-only selection analysis, and high-risk over-editing tests.

Additional metrics:

- Preserve harmony score.
- Preserve melody score.
- Preserve rhythm score.
- Over-editing penalty.
- Partial apply success rate.
- Explanation success rate.
- Average patch latency.

Outputs:

- `evaluation/results/score_editing_v07_results.csv`
- `evaluation/results/score_editing_v07_summary.json`
- `evaluation/results/score_editing_v07_table.tex`
- `evaluation/results/score_editing_v07_failure_cases.json`

## Reporting

Include:

1. Aggregate automatic metrics.
2. Per-category metric table.
3. Example generated score.
4. Validation failure cases.
5. Revision before/after examples.
6. Human evaluation descriptive statistics.
7. Score editing patch previews and accept/reject examples.

## V0.8 Workbench Editing Benchmark

Run:

```powershell
python -m evaluation.workbench_editing.run_workbench_edit_eval --max-prompts 3
python -m evaluation.workbench_editing.summarize_workbench_edit_results
```

The V0.8 prompt set contains 60 app-facing editing tasks covering note input, keyboard shortcuts, drag pitch editing, selection mapping, left-hand accompaniment generation, autosave/recovery, project migration, Agent continuation, and manual-edit preservation.

Primary metrics include note input success rate, keyboard shortcut success rate, drag edit success rate, selection mapping success rate, undo/redo success rate, autosave recovery success rate, project migration success rate, Agent preserve manual edit score, accompaniment generation success rate, MusicXML valid after edit rate, and overall workbench edit score.

Outputs are written to `evaluation/results/workbench_editing_v08_results.csv`, `workbench_editing_v08_summary.json`, `workbench_editing_v08_table.tex`, and `workbench_editing_v08_failure_cases.json`.
