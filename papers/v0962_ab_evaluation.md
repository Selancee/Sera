# V0.96.2 A/B Evaluation

The V0.96.2 benchmark lives in `evaluation/v0962_phrase_level_melody/`. It generates final ScoreDocuments for jazz, pop, classical, romantic, Chinese, and cyberpunk phrase prompts, then computes metrics from the final right-hand notes.

Metrics include phrase contour score, motif development score, mechanical repetition penalty, target-tone hit rate, tension/release curve match, cadence preparation score, accompaniment interaction score, style phrase match score, melody expectation score, and final score musicality proxy.

The A/B comparison simulates a V0.96.1-style template baseline by replacing final right-hand pitches with a repeated measure cell while preserving the same final score rhythm. This makes the comparison focus on phrase-level pitch planning rather than rhythmic variety alone.

The output files are:

- `evaluation/results/v0962_phrase_melody_results.csv`
- `evaluation/results/v0962_ab_comparison_results.csv`
- `evaluation/results/v0962_summary.json`
- `evaluation/results/v0962_table.tex`
- `evaluation/results/v0962_failure_cases.json`
