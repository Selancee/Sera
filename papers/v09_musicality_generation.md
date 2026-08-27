# V0.9 Musicality Generation

Sera V0.9 adds a deterministic musicality layer shared by rule-based, hybrid, and model-conditioned generation.

Engines:

- Rhythm Engine: dotted, eighth, sixteenth, syncopated, rest, and cadence-stable patterns.
- Motif Engine: seed motif, repetition, sequence, inversion, variation, and cadence resolution.
- Harmony Engine: common major, minor, jazz, beginner, and pentatonic progressions.
- Accompaniment Engine: block chords, arpeggios, Alberti bass, bass-chord, waltz bass, pedal point, and sparse beginner bass.
- Texture Engine: monophonic, melody-accompaniment, chordal, arpeggiated, waltz, Alberti, bass-chord, and pentatonic open textures.
- Cadence Engine: phrase-level half cadences and final authentic or modal endings.
- Dynamics Engine: phrase-level dynamic contrast and simple crescendo/diminuendo metadata.
- Musicality Postprocessor: repairs excessive quarter-note output, missing accompaniment, missing cadence, repeated rhythms, empty measures, and narrow range cases.

The default piano output now contains right-hand melody and left-hand accompaniment. Generation metadata records the profile, rhythm patterns, motifs, harmony plan, texture, cadence, accompaniment, dynamics, and postprocess report so the Workbench and Agent can reuse musical intent during local edits.
## V0.92 Style Profile Bridge

V0.92 extends the V0.9 musicality engines with custom style profile inputs. The engines remain rule-based, but they now receive explicit parameters such as rhythm density, syncopation, texture, accompaniment style, harmony flavor, cadence strength, and dynamic contrast.

This bridge is intentionally separate from larger model training. The next model should learn against stable `ScoreDocument` outputs and preserved style profiles, rather than against plan-based preview artifacts.

## V0.93 Musicality Repair

V0.93 adds a musicality validator that checks whether default piano output is non-monophonic, has sufficient left-hand activity, avoids quarter-note dominance, contains rhythmic variety, and includes a final cadence. Failed reports can trigger postprocessing or focused regression failures rather than hiding weak output behind MusicXML validity.

The notation normalizer also supports musicality by making dotted and eighth-note patterns exportable as legal measure contents before MIDI and preview artifacts are generated.
