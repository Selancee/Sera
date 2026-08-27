# V0.9 Precision Editing

Sera V0.9 introduces a MuseScore-like editing location model while preserving the V0.8 ScoreDocument and ScoreOperation architecture.

Core components:

- `ScoreCursor`: measure, beat, staff, voice, offset, pitch, duration, mode, snap, and validation state.
- `BeatGrid`: maps empty measure clicks to beat/eighth/sixteenth/triplet offsets.
- `StaffLane`: maps vertical position to right hand or left hand and pitch.
- `HitAreaOverlay`: expands note/rest hit targets and chooses the nearest target when areas overlap.
- `LocationBar`: keeps the current editing position visible at all times.

The main design change is that notehead hit-testing is no longer the only way to locate the score. If an event hit fails, the click falls back to Beat Grid localization and still moves the Score Cursor. This supports stable select, input, modify, and undo workflows even with fallback rendering or partial OSMD mappings.
