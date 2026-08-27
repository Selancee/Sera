# V0.91 Click-To-Notate Editing

V0.91 adds direct click-to-notate input on top of the V0.9 Score Cursor and Beat Grid. In select mode, clicking an existing event selects it and clicking empty staff space moves the cursor. In note-input mode, the same click is interpreted as a notation command: horizontal position maps to measure offset, vertical position maps to pitch, and the current duration, dotted state, accidental, staff, and voice become a `ScoreOperation`.

The click path is deliberately independent of OSMD notehead internals. Enlarged hit areas are tried first. If no event is hit, Beat Grid localization supplies the nearest measure and offset. Pitch mapping then uses treble or bass staff geometry to infer an octave-aware pitch. Low-confidence pitch mappings still move the cursor and produce LocationBar feedback, but invalid insertions are blocked.

Every click insertion remains undoable because it is represented as `insert_note`, `insert_rest`, or `convert_rest_to_note`. This preserves the Workbench contract that manual edits go through `ScoreOperation` rather than raw MusicXML mutation.

Current limitations: pitch mapping is deterministic and layout-aware, but not yet a full engraving-engine semantic model. Complex tuplets, ornaments, fingering, lyrics, and MIDI keyboard input remain out of scope.
