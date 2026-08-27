# V0.96.1 Style Realization Evaluation

The V0.96 evaluation checked profile builders and hand-written melody cases. V0.96.1 adds an end-to-end benchmark that generates final scores and inspects the resulting ScoreDocument.

The benchmark measures final melody style match, final harmony style match, actual voicing style match, jazz extension presence, jazz plain-triad failure, pop hook contour, classical cadence behavior, Chinese pentatonic note rate, cyberpunk ostinato realization, romantic line range, candidate melody diversity, candidate harmony diversity, and metadata-score consistency.

The evaluation writes CSV, JSON, LaTeX, and failure-case artifacts under `evaluation/results/`. These metrics remain proxies, but they directly test what the user sees and hears rather than only testing intermediate metadata.

V0.96.2 extends this idea with A/B phrase evaluation. The benchmark compares the final phrase-melody score against a simulated repeated-template baseline built over the same final score rhythm, so improvements are attributed to melody planning rather than only rhythm differences.
