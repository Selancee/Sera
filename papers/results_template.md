# Results Template

| Mode | Validity | MIDI success | Rhythm diversity | Quarter dominance | Interval variety | Cadence presence | Overall musicality |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V0.4 model_based |  |  |  |  |  |  |  |
| V0.4 rule_based |  |  |  |  |  |  |  |
| V0.5 model_fragment |  |  |  |  |  |  |  |
| V0.5 hybrid |  |  |  |  |  |  |  |
| V0.5 hybrid without postprocess |  |  |  |  |  |  |  |

Use `evaluation/results/v05_ablation_table.tex` for the paper table after running the comparison script.

## V0.6 Score Editing Results

| Metric | Value |
| --- | ---: |
| Patch validity rate |  |
| Patch application success rate |  |
| MusicXML valid after edit rate |  |
| Constraint respect score |  |
| Selection respect score |  |
| Prompt alignment edit score |  |
| Validation warning reduction |  |
| Average patch size |  |
| Undo/redo success rate |  |
| User acceptance proxy score |  |

Use `evaluation/results/score_editing_table.tex` after running the V0.6 score-editing evaluation.

## V0.7 Score Editing Results

| Metric | Value |
| --- | ---: |
| Patch validity rate |  |
| Patch application success rate |  |
| MusicXML valid after edit rate |  |
| Selection respect score |  |
| Constraint respect score |  |
| Preserve harmony score |  |
| Preserve melody score |  |
| Preserve rhythm score |  |
| Prompt alignment edit score |  |
| Over-editing penalty |  |
| Partial apply success rate |  |
| Undo/redo success rate |  |
| Explanation success rate |  |
| Average patch latency ms |  |

Use `evaluation/results/score_editing_v07_table.tex` after running the V0.7 score-editing evaluation.

## V0.8 Workbench Editing Results

| Metric | Value |
| --- | ---: |
| Note input success rate |  |
| Keyboard shortcut success rate |  |
| Drag edit success rate |  |
| Selection mapping success rate |  |
| Undo/redo success rate |  |
| Autosave recovery success rate |  |
| Project migration success rate |  |
| Agent preserve manual edit score |  |
| Accompaniment generation success rate |  |
| MusicXML valid after edit rate |  |
| Overall workbench edit score |  |

Use `evaluation/results/workbench_editing_v08_table.tex` after running the V0.8 workbench-editing evaluation.
## V0.9 Result Tables

| Precision metric | Score |
| --- | ---: |
| note_hit_success_rate | |
| measure_hit_success_rate | |
| beat_grid_snap_success_rate | |
| cursor_navigation_success_rate | |
| note_input_success_rate | |
| keyboard_shortcut_success_rate | |
| staff_voice_switch_success_rate | |
| user_location_visibility_score | |
| operation_reversibility_rate | |

| Musicality metric | Score |
| --- | ---: |
| rhythmic_diversity_score | |
| dotted_rhythm_presence_rate | |
| eighth_note_presence_rate | |
| sixteenth_note_presence_rate | |
| rest_variety_score | |
| quarter_note_dominance_penalty | |
| melodic_range_score | |
| motif_recurrence_score | |
| cadence_presence_score | |
| accompaniment_presence_rate | |
| left_hand_activity_score | |
| texture_variety_score | |
| dynamic_contrast_score | |
| overall_musicality_proxy_score | |
# V0.91 Results Template Addendum

| Metric | Value |
| --- | ---: |
| click_to_notate_success_rate | |
| pitch_mapping_accuracy_proxy | |
| duration_mapping_accuracy_proxy | |
| dotted_note_input_success_rate | |
| rest_input_success_rate | |
| measure_overflow_prevention_rate | |
| location_bar_feedback_completeness | |
| score_initial_readability_score | |
| render_fallback_success_rate | |
| translation_coverage_rate | |
| zh_cn_translation_coverage_rate | |
| desktop_packaging_readiness_score | |
## V0.92 Results Tables

| Metric group | Metric | Value |
| --- | --- | --- |
| Score consistency | score_document_present_rate | TBD |
| Score consistency | musicxml_score_event_match_rate | TBD |
| Score consistency | score_midi_event_match_rate | TBD |
| Custom style | custom_style_preservation_rate | TBD |
| Custom style | cyberpunk_profile_success_rate | TBD |
| Custom style | style_profile_application_rate | TBD |
| Layout | wrapped_layout_success_rate | TBD |
| Layout | measures_per_system_compliance_rate | TBD |
| Layout | readability_proxy_score | TBD |

Use `evaluation/results/v092_table.tex` for the paper-ready LaTeX table after running the V0.92 evaluation.

## V0.93 Results Tables

| Metric group | Metric | Value |
| --- | --- | ---: |
| Real score source | real_score_preview_rate | TBD |
| Real score source | fake_score_blocked_rate | TBD |
| Real score source | real_playback_source_rate | TBD |
| Real score source | plan_measure_dependency_count | TBD |
| Notation grammar | measure_duration_valid_rate | TBD |
| Notation grammar | rest_grouping_valid_rate | TBD |
| Notation grammar | dotted_duration_valid_rate | TBD |
| Notation grammar | tie_split_valid_rate | TBD |
| Musicality | non_monophonic_rate | TBD |
| Musicality | left_hand_activity_score | TBD |
| Musicality | rhythmic_variety_score | TBD |
| Musicality | cadence_presence_rate | TBD |
| Layout | wrapped_layout_success_rate | TBD |
| Layout | max_measures_per_system_compliance_rate | TBD |
| Layout | score_visibility_success_rate | TBD |

Use `evaluation/results/v093_table.tex` after running `python -m evaluation.v093_real_score_and_notation.run_v093_eval`.

## V0.95 Results Tables

| Metadata metric | Value |
| --- | ---: |
| title_key_consistency_rate | |
| work_title_key_consistency_rate | |
| metadata_sync_success_rate | |
| composer_export_success_rate | |
| composer_edit_success_rate | |

| Melody-line metric | Value |
| --- | ---: |
| melody_line_extraction_success_rate | |
| left_hand_exclusion_success_rate | |
| cross_measure_tritone_rate | |
| melody_line_large_leap_rate | |
| unresolved_cross_measure_leap_rate | |
| melody_repair_success_rate | |

Use `evaluation/results/v095_table.tex` after running `python -m evaluation.v095_metadata_melody_line.run_v095_eval`.
## V0.96 Result Tables

| System | Leap reversal | Mean regression | Closure | Harmony style match | Role coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| V0.96 rule-based candidates | TBD | TBD | TBD | TBD | TBD |
| V0.96 hybrid candidates | TBD | TBD | TBD | TBD | TBD |

| Style | Expected harmony evidence | Observed profile | Voice-leading warnings |
| --- | --- | --- | --- |
| Jazz | ii-V-I, extensions, rootless options | TBD | TBD |
| Chinese | pentatonic/open fifth/quartal/pedal | TBD | TBD |
| Pop | I-V-vi-IV family, sus/add9/slash | TBD | TBD |
| Cyberpunk | modal minor, pedal, ostinato, sus/quartal | TBD | TBD |

## V0.96.1 Final Score Tables

| Metric | Value |
| --- | ---: |
| final_melody_style_match_rate | |
| final_harmony_style_match_rate | |
| actual_voicing_style_match_rate | |
| jazz_actual_extension_presence_rate | |
| jazz_plain_triad_failure_rate | |
| chinese_pentatonic_actual_note_rate | |
| cyberpunk_ostinato_actual_rate | |
| candidate_actual_melody_diversity_score | |
| candidate_actual_harmony_diversity_score | |
| metadata_score_consistency_rate | |

Use `evaluation/results/v0961_table.tex` after running `python -m evaluation.v0961_final_score_style_integration.run_v0961_eval`.

## V0.96.2 Phrase-Level Melody Tables

| Metric | Value |
| --- | ---: |
| phrase_contour_score | |
| motif_development_score | |
| mechanical_repetition_penalty | |
| target_tone_hit_rate | |
| tension_release_curve_match_score | |
| cadence_preparation_score | |
| accompaniment_interaction_score | |
| style_phrase_match_score | |
| melody_expectation_score | |
| final_score_musicality_proxy | |

| A/B metric | V0.96.2 phrase | Simulated V0.96.1 template |
| --- | ---: | ---: |
| final_score_musicality_proxy | | |
| mechanical_repetition_penalty | | |
| melody_fingerprint_distinctness | | |

Use `evaluation/results/v0962_table.tex` after running `python -m evaluation.v0962_phrase_level_melody.run_v0962_eval`.
