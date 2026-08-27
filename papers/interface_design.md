# Interface Design Notes

## Score Workbench

The V0.6 interface adds a dedicated Workbench tab next to the existing generation, plan, validation, evaluation, and model views. The workbench is organized as a production tool rather than a landing page:

- Top toolbar: project actions, import/export, undo/redo, playback, zoom, and editing mode.
- Left rail: note, duration, dynamic, articulation, and Agent tool palettes.
- Center canvas: editable SVG fallback rendering with measure labels, harmony labels, note selection, patch overlays, validation highlights, and playback highlights.
- Right inspector: selected note or measure properties, Agent edit prompt, patch preview, validation report, and prompt-alignment scores.
- Bottom status/timeline: measure navigation, operation history, and current workbench status.

The first renderer is intentionally simple. It provides event-level selection and edit plumbing without depending on a full engraving library. OpenSheetMusicDisplay, VexFlow, or a dedicated notation renderer can replace this adapter later without changing the canonical `ScoreDocument` or operation model.

## V0.7 Workbench UI Additions

V0.7 adds a renderer selector to the toolbar with `auto`, `osmd`, `vexflow`, and `fallback` modes. The status bar reports the active renderer, render state, and render time. OpenSheetMusicDisplay is used when available; if it fails, the workbench keeps the SVG fallback and displays the fallback reason instead of blocking editing.

Selection is upgraded to a reusable state model with click-to-select, modifier multi-select, range selection, marquee measure selection, Escape clear, and Ctrl/Cmd+A select all. Agent tools read the selected range directly from this state.

The Patch Preview panel now includes diff counts for added, removed, changed, pitch, duration, harmony, and cadence changes. It also displays prompt-alignment sub-scores, patch validation recommendation, over-editing risk, and operation-level checkboxes for partial apply. The Agent panel exposes preserve constraints, target difficulty, patch size, target staff, and target voice controls, plus an explain-only action.

## V0.8 Notation Editing Interface

V0.8 reorganizes the toolbar around notation editing. The top bar exposes Select Mode, Note Input Mode, duration buttons, rest/dot/accidental controls, tie/slur actions, staff and voice selectors, undo/redo, playback, loop selection, zoom, fit width, renderer selection, and export buttons. The left rail adds a Note Input panel with cursor state, duration selection, staff/voice/accidental/octave controls, chord-tone mode, and auto-fill rests.

The center canvas uses the renderer adapter for visual display and a transparent overlay for interaction. The overlay supports event-first hit testing, nearest-event fallback, measure fallback, drag selection, selected-note highlighting, patch range highlighting, validation warning highlighting, and playback measure highlighting. A Hit Mapping panel exposes renderer mode, selected event ids, dirty measures, mapping confidence, and fallback reason for debugging and paper screenshots.

The bottom playback scrubber links score position with the current measure and event. If real MIDI rendering is unavailable, the fake playback map still highlights measures and events so editing remains usable during demonstrations.
## V0.9 Interface Additions

The V0.9 Workbench makes location visible as a first-class editing surface. `ScoreCursorOverlay` draws the active insertion cursor over both fallback and OSMD-overlay rendering paths. `BeatGridOverlay` exposes snap points for beat, eighth, sixteenth, and triplet editing. `StaffLaneOverlay` highlights the right-hand or left-hand lane, and `HitAreaOverlay` shows the expanded event targets used for tolerant note/rest selection.

`LocationBar` is persistent and shows measure, beat, staff, voice, pitch, duration, mode, snap, selection count, and validation state. This reduces dependence on accurate notehead clicks and supports a MuseScore-like sequence of select, input, modify, and undo.
# V0.91 Interface Addendum

The Workbench now previews click-to-notate actions before insertion. Hovering in Note Input Mode shows a ghost note or rest with inferred pitch, duration, dotted state, staff, voice, and beat. The LocationBar reports hover pitch, hover beat, click action, insertion validity, snap, dotted state, and accidental mode, so the user can understand the result before committing a click.

Readable layout controls were added to reduce visual ambiguity: fit-width default, layout mode selection, zoom presets, Reset View, Re-render Score, and MusicXML Text Preview. These controls make rendering state visible rather than forcing users to infer whether a blank or tiny score is caused by layout, renderer failure, or missing score data.
## V0.92 Rendered Score And Source Indicators

The Generate page separates Agent Plan from Rendered Score. The score preview uses `score_document` first and real MusicXML as fallback; it no longer draws simplified plan bars. Score Source and Playback Source badges show whether the user is seeing `ScoreDocument`, MusicXML fallback, MIDI export, or ScoreDocument event playback.

The Consistency Report panel exposes event-count and mismatch diagnostics directly in the UI. This makes source disagreement visible before the user opens the Workbench or exports a file.

Readable layout uses wrapped systems with shared measure geometry. The fallback renderer, Beat Grid, Staff Lane overlay, hit areas, and Score Cursor all read the same system coordinates, so a wrapped 16-measure score remains editable and visually aligned.

## V0.93 Interface Addendum

The Generate page now treats Rendered Score and Agent Plan as separate surfaces. Score Source badges distinguish `backend_svg`, `backend_png`, `ScoreDocument`, `MusicXML text`, and `Unavailable`. Playback Source badges distinguish MIDI export, backend note events, ScoreDocument events, and unavailable playback.

If no authoritative score source exists, the preview shows a clear unavailable state instead of drawing notation from plan data. A Render Source Debug panel exposes run id, score id, preview render status, and backend render URL. The validation panel also shows notation grammar status: measure duration, rest grouping, dotted duration, tie validity, and normalizer fix counts.

## V0.95 Interface Addendum

The Generate page now exposes score-level metadata through `ScoreMetadataPanel`. Users can edit title and composer before opening the Workbench or downloading MusicXML, and these edits update the canonical ScoreDocument rather than only changing visible text. `KeyConsistencyPanel` shows prompt key, UI key, resolved key, ScoreDocument key, title key, and MusicXML key, including stale-title warnings when synchronization is not possible.

The Workbench Inspector adds editable Title and Composer fields that dispatch `change_title` and `change_composer` ScoreOperations. The Workbench header mirrors the current title, composer, and key so metadata edits have immediate visible feedback. `MelodyLineReportPanel` labels diagnostics as primary-melody based and explicitly distinguishes them from the mixed playback event stream.
