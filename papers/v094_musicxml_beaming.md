# V0.94 MusicXML Beaming

V0.94 added meter-aware MusicXML beam metadata for generated eighth and sixteenth notes. The beaming layer assigns begin, continue, and end tags within simple 4/4, 3/4, and 6/8 groups, avoiding orphan beam tags on isolated short notes.

V0.95 keeps the same export path but synchronizes title and composer before final MusicXML is written. This means beaming, work title, composer, and key signature all come from the canonical ScoreDocument export.
