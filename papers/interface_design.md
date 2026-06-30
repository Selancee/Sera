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
