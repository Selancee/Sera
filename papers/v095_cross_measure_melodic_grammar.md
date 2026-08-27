# V0.95 Cross-Measure Melodic Grammar

V0.95 extends melodic grammar beyond isolated measure fragments. The validator checks the interval from the last primary melody note of measure N to the first primary melody note of measure N+1, with special attention to tritone-like jumps, octave-plus leaps, unresolved large leaps, and same-direction stepwise runs that cross measure boundaries.

Large leaps are expected to resolve by contrary stepwise motion unless they occur as a controlled phrase-boundary exception. Beginner and intermediate settings are stricter than advanced settings. When repair is possible, Sera adjusts the next measure opening note to a nearby consonant target while preserving rhythm duration, harmony metadata, and left-hand accompaniment.

The report is stored as `generation_metadata.cross_measure_melodic_grammar_report` and evaluated by `evaluation/v095_metadata_melody_line`.
## V0.96 Extension

The cross-measure melodic grammar report remains active in V0.96 and is used by candidate ranking as one component of `melodic_grammar_score`. The new expectation validator is complementary: it evaluates phrase-level tendency and closure, while the V0.95 cross-measure layer continues to focus on boundary leaps and repair.
