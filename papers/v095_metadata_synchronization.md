# V0.95 Metadata Synchronization

V0.95 addresses stale score titles caused by provisional prompt understanding. Earlier stages could create a title such as `Classical Sketch in C major`; later UI control resolution could correctly set the score key to `A minor`, leaving title and MusicXML `<work-title>` inconsistent.

The metadata synchronization service runs after final controls are resolved and before MusicXML export. It aligns intent key, resolved key, ScoreDocument key, title, composer, ScoreDocument metadata, MusicXML work title, and MusicXML key signature. If a generated title contains a stale key, Sera rewrites or neutralizes it. Explicit user titles are preserved unless they contain stale generated key text.

The generation response records `metadata_sync_report` and `key_consistency_report`, and the frontend shows the result in `ScoreMetadataPanel` and `KeyConsistencyPanel`.
