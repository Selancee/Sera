# V0.8 Workbench App Design

V0.8 upgrades Sera from a generation previewer into a fallback-safe notation workbench. The central design decision is to keep `ScoreDocument` as the canonical state and use renderer adapters only for display. OSMD, VexFlow, and SVG fallback can change without changing operation replay, patch validation, or project serialization.

## Editing Loop

1. Import or generate a score.
2. Render with OSMD/VexFlow/fallback.
3. Select note, rest, measure, staff, or voice.
4. Edit through mouse, keyboard, Inspector, or palette.
5. Apply a `ScoreOperation`.
6. Mark dirty measures and run lightweight validation.
7. Refresh MusicXML preview and playback map.
8. Optionally ask the Agent for a local patch.
9. Preview, partially apply, accept, reject, undo, or redo.

## Fallback Strategy

The fallback SVG renderer is not only an emergency display path; it is the deterministic interaction layer. V0.8 exports event ids into MusicXML and builds overlay hit boxes from ScoreDocument events. When OSMD notehead internals are unstable, Sera still supports event-level selection through overlay hit boxes with debug confidence and fallback reason.

## App-Facing Controls

The toolbar supports Select Mode, Note Input Mode, durations, dot, accidentals, tie/slur, staff, voice, undo/redo, playback, loop, zoom, fit width, renderer mode, and exports. The left rail includes note input cursor controls, note/duration/dynamic/articulation palettes, line/staff tools, generated left-hand accompaniment, and keyboard help. The right rail keeps Inspector, hit mapping debug, Agent tools, patch preview, selection explanation, and validation.
