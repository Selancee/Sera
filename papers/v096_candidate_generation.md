# V0.96 Candidate Generation

A seed no longer directly produces the final score. The run seed derives 3-8 candidate seeds, defaulting to 4. Each candidate is generated, canonicalized into ScoreDocument, validated, scored, and ranked. The selected candidate is returned to the user; rejected candidates are summarized in metadata.

Ranking combines melody expectation, harmony style, notation validity, melodic grammar, style match, novelty, accompaniment, and role coverage. This is deterministic under a fixed run seed.

V0.96.1 adds final-score diversity accounting. Candidate fingerprints are separated into melody, rhythm, and harmony/voicing fingerprints computed from the final ScoreDocument, so a candidate set only counts as diverse when the actual generated music differs. Candidate metadata now reports `candidate_actual_diversity`.
