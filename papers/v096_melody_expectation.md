# V0.96 Melody Expectation Layer

V0.96 implements practical expectation-theory-inspired melody checks rather than training a larger model. The validator computes leap reversal, mean regression, pitch proximity, directional inertia, registral return, gap fill, tonal anchoring, closure, unresolved dissonance count, and unresolved tritone count.

The layer is used in three places: candidate ranking, melody repair experiments, and evaluation. It extends, but does not replace, V0.95 melody-line extraction and cross-measure melodic grammar.

V0.96.1 integrates the layer into the final rule-based generator. Right-hand notes are now generated as multiple expectation candidates per measure, ranked by the melody expectation validator, checked by melodic grammar, and then converted into the actual MusicXML note stream. The previous degree-label melody template remains only as fallback. This distinction matters because V0.96 metadata-level reports could pass while the audible score still used the old melody path.

V0.96.2 changes the normal source again: phrase-level melody generation now creates the right-hand line first, and the expectation validator scores that phrase output. The older expectation `_style_shapes` generator remains fallback only. This keeps expectation theory as a validator/ranker while allowing motif memory, contour, target tones, and cadence preparation to shape the actual phrase.
