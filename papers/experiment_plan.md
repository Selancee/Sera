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
- TODO: direct LLM-to-MusicXML baseline.
- TODO: trained symbolic Transformer baseline using local MusicXML/PDMX/MetaScore/POP909/Lakh-derived data.

## Reporting

Include:

1. Aggregate automatic metrics.
2. Per-category metric table.
3. Example generated score.
4. Validation failure cases.
5. Revision before/after examples.
6. Human evaluation descriptive statistics.
