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

## V0.93 Real Score And Notation Benchmark

Run:

```powershell
python -m evaluation.v093_real_score_and_notation.run_v093_eval --max-prompts 3
```

The benchmark adds hard regression metrics for real score source usage, fake score blocking, real playback source usage, notation grammar validity, musicality repair, and wrapped layout readability. It explicitly counts `plan.measures` dependency in final preview/playback components and reports backend preview-render success separately from ScoreDocument or MusicXML fallback success.

Primary outputs:

- `evaluation/results/v093_real_score_results.csv`
- `evaluation/results/v093_notation_results.csv`
- `evaluation/results/v093_musicality_results.csv`
- `evaluation/results/v093_layout_results.csv`
- `evaluation/results/v093_summary.json`
- `evaluation/results/v093_failure_cases.json`
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
## V0.9 Precision And Musicality Benchmark

The V0.9 benchmark adds two groups of metrics. Precision metrics measure note hit success, measure hit success, beat-grid snap success, cursor navigation, note input, keyboard shortcuts, drag pitch, staff/voice switching, location visibility, and operation reversibility. Musicality metrics measure rhythmic diversity, dotted/eighth/sixteenth presence, rest variety, quarter-note dominance penalty, melodic range, motif recurrence, cadence presence, accompaniment presence, left-hand activity, texture variety, dynamic contrast, and an overall proxy score.

Run:

```powershell
python -m evaluation.v09_precision_and_musicality.run_v09_eval --max-prompts 3
```

The benchmark writes CSV, JSON, TeX, and failure-case artifacts under `evaluation/results/`.
# V0.91 Evaluation Addendum

The V0.91 usability benchmark measures click-to-notate success, pitch mapping proxy accuracy, duration mapping accuracy, dotted note input, rest input, overflow prevention, LocationBar feedback completeness, initial score readability, render fallback success, translation coverage, Simplified Chinese coverage, and desktop packaging readiness.

Run:

```powershell
python -m evaluation.v091_usability.run_v091_usability_eval --max-prompts 3
```

The benchmark is a proxy evaluation for engineering readiness. Human studies are still needed for perceived notation speed, musical intent preservation, and translation quality.
## V0.92 Evaluation Addendum

V0.92 adds `evaluation/v092_unified_score_and_style/` to measure whether the generated score source, custom style profile, and readable layout contracts hold.

Score consistency metrics include `score_document_present_rate`, `musicxml_present_rate`, `midi_present_rate`, `musicxml_score_event_match_rate`, `score_midi_event_match_rate`, `mismatch_count_mean`, and `authoritative_score_usage_rate`.

Custom style metrics include preservation rates for cyberpunk, anime, cinematic, new age, and game soundtrack prompts, plus `style_profile_application_rate`.

Layout metrics include `wrapped_layout_success_rate`, `measures_per_system_compliance_rate`, `first_system_visibility_rate`, `staff_overlap_failure_rate`, and a readable-layout proxy score.

## V0.95 Metadata And Melody-Line Benchmark

V0.95 adds `evaluation/v095_metadata_melody_line/` to measure metadata synchronization and melody-line diagnostics.

Run:

```powershell
python -m evaluation.v095_metadata_melody_line.run_v095_eval --max-prompts 3
```

Metadata metrics include `title_key_consistency_rate`, `work_title_key_consistency_rate`, `metadata_sync_success_rate`, `composer_export_success_rate`, and `composer_edit_success_rate`.

Melody-line metrics include `melody_line_extraction_success_rate`, `left_hand_exclusion_success_rate`, `cross_measure_tritone_rate`, `melody_line_large_leap_rate`, `unresolved_cross_measure_leap_rate`, and `melody_repair_success_rate`.

The case set covers prompt C major vs UI A minor, prompt A minor vs default UI C major, no prompt key with UI A minor, title edits, composer edits, right-hand melody with left-hand accompaniment, cross-measure tritone, cross-measure octave-plus leap, and mixed playback event streams that must not be treated as melody.
## V0.96 Expectation, Harmony, And Track Preparation Benchmark

The V0.96 benchmark evaluates three dimensions:

- Melody expectation: leap reversal, mean regression, unresolved large-leap rate, unresolved tritone rate, and phrase closure.
- Style harmony: jazz extensions, Chinese pentatonic/open sonorities, classical voice-leading penalties, pop progression match, and cyberpunk/electronic modal-pedal mapping.
- Multi-track preparation: whether the selected ScoreDocument exposes lead melody, harmony, and bass roles through optional tracks and role coverage metadata.

Run:

```powershell
.\.venv\Scripts\python.exe -m evaluation.v096_expectation_harmony_orchestration.run_v096_eval --max-prompts 3
```

## V0.96.1 Final Score Style Integration Benchmark

V0.96.1 adds `evaluation/v0961_final_score_style_integration/`. Unlike the V0.96 benchmark, it generates final scores and inspects the resulting ScoreDocument notes.

Run:

```powershell
.\.venv\Scripts\python.exe -m evaluation.v0961_final_score_style_integration.run_v0961_eval --max-prompts 3
```

Metrics include final melody style match, final harmony style match, actual voicing style match, jazz extension presence, jazz plain-triad failure, Chinese pentatonic actual note rate, cyberpunk ostinato realization, candidate melody diversity, candidate harmony diversity, and metadata-score consistency.

## V0.96.2 Phrase-Level Melody Benchmark

V0.96.2 adds `evaluation/v0962_phrase_level_melody/`. It generates final ScoreDocuments for jazz, pop, classical, romantic, Chinese, and cyberpunk phrase prompts, then computes metrics from the actual right-hand events.

Run:

```powershell
.\.venv\Scripts\python.exe -m evaluation.v0962_phrase_level_melody.run_v0962_eval --max-prompts 3
```

Metrics include phrase contour score, motif development score, mechanical repetition penalty, target-tone hit rate, tension/release curve match, cadence preparation score, accompaniment interaction score, style phrase match score, melody expectation score, and final score musicality proxy. The A/B table compares the V0.96.2 phrase melody with a simulated V0.96.1-style repeated template baseline over the same final score rhythm.
