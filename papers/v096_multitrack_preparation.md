# V0.96 Multi-Track Preparation

ScoreDocument now supports optional `tracks` with role, instrument, part, staff, and voice fields. Existing piano scores remain valid because missing tracks are inferred from right-hand and left-hand staff usage.

V0.96 does not implement full orchestration. It prepares metadata and validation surfaces for future lead melody, harmony, bass, and rhythmic roles while keeping MusicXML export backward compatible.

V0.96.1 does not add orchestration UI. It uses the final ScoreDocument track and staff roles when computing actual harmony style, role coverage, and candidate diversity, so multi-track preparation participates in final-score validation rather than only metadata reporting.
