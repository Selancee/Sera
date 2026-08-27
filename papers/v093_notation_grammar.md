# V0.93 Notation Grammar

V0.93 introduces `backend/notation/` as a rule layer between generation and MusicXML export. Duration math uses `fractions.Fraction` rather than floating-point equality. Meter rules cover 4/4, 3/4, and 6/8 capacities and beat groups.

The notation normalizer fills empty measures and gaps with grouped rests, prevents event overflow, and splits overlong notes across barlines with simple ties. The validator checks measure duration, dotted duration labels, tie values, staff names, voice numbers, and basic rest grouping.

This layer is not a complete engraving system. It is a hard regression guard that makes generated MusicXML more readable and prevents obviously illegal measure contents before playback and preview generation.
