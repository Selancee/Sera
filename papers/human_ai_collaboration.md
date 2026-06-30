# Human-AI Collaboration In Sera V0.6

V0.6 reframes Sera as a co-editing system. The human can generate a draft, inspect the score, select a local passage, perform manual edits, or ask the Agent to propose a patch. The Agent does not overwrite the score directly. It returns a localized `ScorePatch` with operations, rationale, expected effect, prompt-alignment notes, and risks.

The collaboration loop is:

1. Human selects notes or measures.
2. Human writes an edit instruction or chooses an Agent tool.
3. Agent proposes a patch.
4. Sera previews the before/after difference and validation report.
5. Human accepts, rejects, partially applies, or regenerates the patch.
6. Sera records the operation and patch history for replay and research analysis.

This design supports paper analysis because every action is explicit: manual operations, Agent operations, prompt-alignment metrics, validation outcomes, and user acceptance decisions.

## V0.7 Partial Acceptance And Explain-Only Support

V0.7 strengthens the collaboration loop by separating three Agent roles:

1. Suggesting a patch.
2. Explaining a selected passage without modifying it.
3. Repairing or regenerating a patch after validation feedback.

The patch preview now includes a validation recommendation and over-editing risk. Users can accept the full patch, reject it, regenerate it, or apply selected operations only. Partial apply is important for collaboration because it lets the human preserve authorship over specific details while still using the Agent for local alternatives. Undo/redo remains available after both manual edits and partial Agent edits, and the operation history records which operations came from the user versus the Agent.

## V0.8 Manual-Edit-Aware Collaboration

V0.8 makes manual editing first-class. A user can enter notes with the keyboard, drag pitches, switch staff/voice, add rests or ties, generate a left-hand accompaniment, and then ask the Agent to continue from those edits. The Agent request includes recent manual operations, dirty measures, selected notes, validation warnings, and playback position. This gives the Agent a concrete local context rather than only a prompt and measure range.

The key collaboration safeguard is preservation of recent manual edits. Broad Agent operations can include `exclude_event_ids`, so a transformation such as "make this more expressive" can avoid notes the user just changed. The operation history then distinguishes user-authored edits, Agent-authored patches, rejected patches, and later manual refinements, making authorship and co-creation sequences easier to audit.
