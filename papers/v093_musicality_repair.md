# V0.93 Musicality Repair

V0.93 adds a musicality validator to make weak generated scores visible. The validator records monophonic penalty, quarter-note dominance, left-hand activity, rhythmic variety, cadence presence, motif presence, warnings, and errors.

Default intermediate piano output should include right-hand melody, left-hand accompaniment in most measures, varied durations, dotted or eighth-note motion, motif metadata, and a final cadence. The validator is a collapse detector, not a replacement for human evaluation.

The V0.93 evaluation reports non-monophonic rate, left-hand activity score, rhythmic variety score, dotted/eighth presence, quarter-note dominance, cadence presence, and phrase-structure proxy score.
