# V0.96.1 Final Score Integration

V0.96.1 addresses the difference between metadata-level musicality and final-score realization. A module is treated as integrated only when it changes the note events that become ScoreDocument, MusicXML, and MIDI.

The right-hand melody path now calls the expectation melody generator and melody candidate ranker before measure XML is emitted. Jazz, pop, and classical have explicit melodic style families, while Chinese, cyberpunk, and romantic keep their earlier specialized profiles.

The harmony path now uses harmony profile progressions as the primary source. Candidate variation selects among style-appropriate progressions rather than replacing them with generic variants. The voicing engine produces actual left-hand pitches, and static triads are fallback only.

The pipeline adds `actual_harmony_style_report`, which inspects final left-hand notes for sevenths, extensions, open fifths, pedal points, ostinato behavior, and plain-triad-only failures. This report can disagree with metadata, and that disagreement is surfaced for debugging.

V0.96.2 keeps this final-score criterion and applies it to phrase melody. The right-hand ScoreDocument events now come from `phrase_melody_engine` in the normal path. Per-measure expectation shapes are retained as fallback, not as the primary melodic source.
