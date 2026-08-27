# System Description Draft

## Overview

Sera is an agentic text-to-score composition system designed for editable symbolic music generation and reproducible MIR / AI music experiments. The system converts a natural-language prompt into a structured composition plan, generates a playable MusicXML score, validates notation quality, optionally revises the plan, and saves all artifacts in an experiment directory.

## Agent Pipeline

The Prompt Understanding Agent parses user prompts into a stable JSON intent. The intent includes title, style, mood, instrumentation, key, meter, tempo, length, form, texture, difficulty, harmony plan, section plan, and revision goals. Missing prompt fields are completed by deterministic defaults. If an OpenAI-compatible LLM provider is configured, Sera merges only schema-safe JSON fields; otherwise it falls back to local rules.

The Composition Planning Agent expands the intent into a measure-level plan. Each measure receives a section label, chord, harmonic function, rhythm profile, density, cadence, motif degrees, texture, and description. This intermediate plan is intended to be inspectable by researchers and editable in future user studies.

## Symbolic Generation

The V0.2 generator is rule-based and MusicXML-first. It supports piano single-line sketches and simplified two-staff piano textures, 4/4, 3/4, and 6/8 meters, major and minor keys, 8, 16, and 32 measure forms, basic harmonic progressions, repeated motifs, motivic variation, controlled range, and cadential closure.

## V0.5 Hybrid Generation

V0.5 keeps the MusicXML-first rule generator as the legality layer and narrows the neural model role to local musicality tasks. The Agent plans form, key, meter, harmony, rhythmic density, melodic contour, cadences, motif strategy, and texture. The rule-based generator assembles measure structure, beat positions, left-hand support, and valid MusicXML. The small model proposes melody fragments, motif variations, cadence melodies, or rhythm rewrites. A postprocess pass reduces excessive quarter-note runs, overlong same-direction stepwise motion, missing cadences, incomplete measures, and pitch-range issues. If any model or postprocess step fails, Sera falls back to the rule-based result.

## Validation and Revision

The MusicXML validator checks XML parsing, music21 parsing when available, plan length match, per-staff/per-voice measure completeness, pitch range, empty measures, MIDI export, and PDF export. The Revision Agent repairs empty or incomplete measure plans and applies user feedback such as "more melancholic", "Chopin-like", "change to triple meter", "lower difficulty", "faster", and "more flowing left hand".

## Research Workbench

The frontend is a React/Vite workbench with prompt entry, parameter shortcuts, Agent plan visualization, score preview, MIDI playback/download, revision input, validation report, export controls, and experiment history. V0.5 adds Research Mode fields for generator mode, model task type, decoding parameters, postprocess report, and musicality proxy metrics. If full engraving is unavailable, the UI presents a simplified score preview and MusicXML/export links.

## V0.6 Score Workbench And Agentic Editing

V0.6 separates score editing from raw MusicXML strings by introducing a canonical `ScoreDocument` event graph. MusicXML is used for import and export, while the workbench stores notes, rests, measures, staves, dynamics, harmony labels, section labels, and annotations as JSON. Manual edits are normalized into `ScoreOperation` objects and appended to an operation history with undo/redo snapshots.

Agentic editing is implemented as a local `ScorePatch` workflow. The Score Editing Agent receives the current `ScoreDocument`, a selected measure range, preserve constraints, and a user instruction. It returns JSON only: a localized patch, rationale, expected effect, prompt-alignment notes, and operations. Patches are previewed first, validated through MusicXML export, and only applied after acceptance. Rejected patches leave the score unchanged.

The first workbench renderer is an SVG fallback that maps editable events to visual note heads, measure regions, harmony labels, section labels, patch overlays, validation highlights, and playback highlights. This is sufficient for interaction and paper screenshots, while full engraving remains a future adapter.

## V0.7 Renderer Adapter And LLM Score Editing

V0.7 upgrades the workbench renderer into an adapter layer with `auto`, `osmd`, `vexflow`, and `fallback` modes. `auto` attempts OpenSheetMusicDisplay using a ScoreDocument-to-MusicXML export path; rendering failures are surfaced in the status bar and automatically fall back to the SVG renderer. VexFlow is represented as an explicit adapter placeholder so future native event-graph engraving can be added without changing the state model. The transparent overlay remains responsible for hit testing, selection highlights, patch highlights, validation warning highlights, and playback position highlights, so renderer libraries do not mutate score state.

The Score Editing Agent now supports a schema-constrained provider path with `SERA_LLM_PROVIDER=mock/openai/deepseek/qwen`. Missing API keys, provider errors, invalid JSON, or failed repair attempts fall back to the deterministic mock planner. Each provider attempt records provider, model, prompt version, raw response, parsed patch, schema errors, fallback reason, and latency. This keeps experiments reproducible while allowing live LLM comparisons.

Patch validation is stricter in V0.7. Preview and apply both produce a `ScorePatchValidationReport` covering target-range validity, operation scope, preserve-constraint violations, structural risks, MusicXML validity after patch, patch size, over-editing risk, and accept/review/reject recommendation. Partial apply lets users accept selected operations or operation categories while rejected operations remain available in patch history.

## Reproducibility

Each run writes an independent folder under `experiments/` containing `prompt.txt`, `plan.json`, `generated.musicxml`, `generated.mid`, `generated.pdf`, `validation_report.json`, `revision_history.json`, `metadata.json`, and `experiment_log.json`. This structure is intended to support paper figures, evaluation tables, and post-hoc failure analysis.

## V0.8 MuseScore-Like Workbench Core

V0.8 shifts the research workbench toward a usable notation editor. The renderer layer still supports `auto`, `osmd`, `vexflow`, and `fallback`, but interaction is stabilized through a deterministic overlay hit map. Each ScoreDocument event is exported with `sera-event-id` metadata, and the workbench builds note/rest/measure bounding boxes with mapping confidence and fallback reasons. If OSMD internals cannot provide stable notehead ids, note-level selection still works through the overlay map.

The editing loop now includes select mode, note input mode, keyboard shortcuts, drag pitch editing, duration/rest/accidental/tie/slur/dynamic/articulation edits, staff/voice switching, simple piano left-hand accompaniment generation, fake playback scrubber, dirty-measure tracking, autosave recovery, and V0.8 project migration. All manual actions remain `ScoreOperation` objects, so undo/redo and operation replay continue to support research analysis.

Agentic editing is manual-edit aware in V0.8. The Agent receives current selection, recent operations, dirty measures, validation warnings, playback position, selected-note summaries, inferred user intent, and a timestamp boundary for preserving recent user edits. Broad Agent operations can carry `exclude_event_ids`, preventing recent manual notes from being overwritten during local transformations.
## V0.9 Precise Localization And Musicality Layer

Sera V0.9 adds a Score Cursor, Beat Grid, Staff Lane model, enlarged Hit Areas, and LocationBar on top of the V0.8 ScoreDocument and ScoreOperation architecture. The cursor records measure, beat, staff, voice, offset, pitch, duration, mode, snap, and validation state. Empty measure clicks no longer depend on exact notehead hits; they resolve through the Beat Grid and update the same cursor state used by the Inspector, StatusBar, and Agent context.

The generation stack now includes a shared musicality layer under `backend/generation/musicality/`. Rhythm, motif, harmony, accompaniment, texture, cadence, dynamics, profile, and postprocess modules provide a deterministic skeleton for rule-based, hybrid, and model-conditioned generation. The default piano path emits right-hand melody plus left-hand accompaniment and metadata for rhythm patterns, motifs, harmony, texture, cadence, accompaniment, dynamics, and postprocess decisions.
# V0.91 Stabilization Addendum

V0.91 extends the V0.9 localization and musicality architecture with a click-to-notate layer, readable layout controls, frontend internationalization, and a Windows packaging path. Click input converts pointer position into a `ScoreOperation` by combining enlarged hit areas, Beat Grid fallback, staff-position pitch mapping, current duration, dotted state, staff, and voice. The backend remains unchanged in its editing contract: manual edits are still applied through ScoreDocument operations and exported back to MusicXML.

The deployment path now includes PyInstaller backend packaging and a staged Electron shell. The packaged backend exposes `/health`, chooses an available local port, and writes runtime port metadata for the frontend shell.
## V0.92 Unified Score Source

V0.92 makes `ScoreDocument` the authoritative score after generation. The first-page preview, Workbench state, MusicXML export, and playback fallback now share the same canonical source. `plan.measures` remains an Agent planning artifact, but it is no longer treated as the rendered score or playback source.

The backend generation response includes `score_document`, `musicxml`, `midi_url`, `exports`, `generation_metadata`, and `consistency_report`. The consistency report compares MusicXML event counts, ScoreDocument event counts, MIDI note events, measure counts, staff coverage, and empty-measure warnings.

Custom style prompts are preserved through `custom_style_tags`, `base_style`, and `style_profile`. These fields let the rule-based musicality engines apply cyberpunk, anime, cinematic, new age, and game soundtrack controls without forcing unknown styles into classical.

## V0.93 Real Score Source And Notation Grammar

V0.93 removes plan-based final rendering and final playback as valid output paths. The Agent plan remains inspectable, but the rendered score must come from backend-rendered MusicXML, canonical ScoreDocument rendering, real MusicXML text, or an explicit unavailable state. Playback must use exported MIDI or note events derived from ScoreDocument.

The backend adds a notation grammar layer between generation and export. Duration math uses rational values, meter rules define 4/4, 3/4, and 6/8 capacity, and the normalizer fills gaps, prevents overflow, and splits overlong events with ties. The notation validator records measure duration, rest grouping, dotted duration, tie, staff, and voice status in generation metadata. Larger model training is postponed until these score-source and notation guarantees remain stable.

## V0.95 Metadata And Melody-Line Layer

V0.95 adds a final metadata synchronization service after prompt/UI control resolution and before MusicXML export. The service aligns `intent.key`, resolved controls, `ScoreDocument.global.key`, `score_document.title`, `score_document.metadata.title`, MusicXML `<work-title>`, and the MusicXML key signature. If a provisional prompt title contains a stale key after an explicit UI override, Sera rewrites or neutralizes the title and records `metadata_sync_report` plus `key_consistency_report`.

V0.95 also separates playback events from melody diagnostics. A melody-line extractor groups canonical ScoreDocument events by staff and voice, selects right-hand voice 1 as the primary melody for piano, and marks left-hand lines as accompaniment. Cross-measure melodic grammar now validates the transition from the final melody note of one measure to the first melody note of the next and reports unresolved tritones, large leaps, phrase-boundary exceptions, and repairs.
## V0.96 Candidate And Harmony Extension

V0.96 adds a control-only generation path, a candidate-before-final pipeline, melody expectation validation, style-aware harmony profiles, voicing and voice-leading reports, and optional ScoreDocument tracks. The larger symbolic model remains deferred; rule-based and hybrid generators still produce valid MusicXML through the existing ScoreDocument canonicalization path.

The generation flow is now:

```text
raw prompt / UI controls -> resolved intent -> run seed -> candidate seeds
  -> candidate generation -> ScoreDocument canonicalization
  -> melody expectation + harmony profile + notation validation
  -> candidate ranking -> selected final score
```

The metadata contract preserves V0.95 reports and adds `candidate_generation`, `melody_expectation_report`, `harmony_profile`, `voicing_report`, `voice_leading_report`, `track_plan`, and `role_coverage_report`.

## V0.96.1 Final Score Integration

V0.96.1 changes the integration criterion: reports are not sufficient unless they affect final ScoreDocument events. The rule-based generator now routes right-hand melody through expectation melody candidates and uses the selected candidate as actual MusicXML notes. Jazz, pop, and classical melodic style families no longer fall back to the generic profile.

Harmony profile progressions are now the source of measure chord labels, and candidate variation selects among style-appropriate profile cells. The voicing engine produces final left-hand notes, with static triads retained only as fallback. The pipeline computes `actual_harmony_style_report` from final ScoreDocument events and uses it in candidate ranking.

## V0.96.2 Phrase-Level Melody Baseline

V0.96.2 replaces the normal right-hand melody source with a phrase-level rule module. The module plans each 4-measure phrase through motif memory, phrase contour, harmonic target tones, tension/release, call-and-response, and cadence preparation before individual measure events are written.

The final ScoreDocument remains the source of truth. `RuleBasedGenerator` generates a `phrase_melody` report before the measure loop, then `_right_hand_events()` consumes the per-measure MIDI lists from that report. The older expectation `_style_shapes` path remains fallback only and is flagged through `hardcoded_shape_fallback_used`.

Candidate ranking now receives phrase contour, motif development, tension/release, target-tone hit, cadence preparation, accompaniment interaction, and mechanical-template penalty metrics. This creates a stronger non-neural baseline before any V0.97 model training.
