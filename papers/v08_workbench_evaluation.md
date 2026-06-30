# V0.8 Workbench Editing Benchmark

The V0.8 benchmark measures whether the Workbench behaves like a usable notation-editing app core rather than only a backend patch API.

## Prompt Types

The benchmark contains 60 tasks across note input, keyboard shortcuts, drag pitch editing, selection mapping, left-hand accompaniment generation, Agent continuation, manual-edit preservation, autosave/recovery, and project migration.

## Metrics

- `note_input_success_rate`
- `keyboard_shortcut_success_rate`
- `drag_edit_success_rate`
- `selection_mapping_success_rate`
- `undo_redo_success_rate`
- `autosave_recovery_success_rate`
- `project_migration_success_rate`
- `agent_preserve_manual_edit_score`
- `accompaniment_generation_success_rate`
- `musicxml_valid_after_edit_rate`
- `overall_workbench_edit_score`

## Baseline

The baseline is the V0.7 Workbench: renderer modes, patch preview, partial apply, and explain selection, but without the V0.8 note-input cursor, drag-edit path, autosave/project migration helpers, or manual-edit-aware Agent context.

## Failure Cases

Expected failures include exact OSMD notehead mapping errors, overfull measures after drag offset changes, ambiguous staff targeting during note input, and Agent patches that are valid JSON but musically too broad. V0.8 records these as validation warnings, fallback reasons, or failure-case rows rather than blocking the entire app.

## Expected Table

Use `evaluation/results/workbench_editing_v08_table.tex` after running:

```powershell
python -m evaluation.workbench_editing.run_workbench_edit_eval --max-prompts 3
python -m evaluation.workbench_editing.summarize_workbench_edit_results
```
