# V0.7 Score Editing Benchmark

## Design

The V0.7 benchmark evaluates Sera's Score Workbench as a local human-Agent editing system rather than a full-score generator. Each trial starts from the same generated piano seed score, selects a measure range, applies an edit instruction, validates the proposed patch, optionally tests partial apply, and records prompt-alignment metrics.

## Prompt Types

The 50-prompt set covers local melody rewriting, left-hand accompaniment rewriting, rhythmic density increase/decrease, preserve melody, preserve harmony, preserve rhythm, cadence insertion, difficulty reduction/increase, pentatonic color, three-beat requests, validation-warning repair, explain-only analysis, high-risk over-editing, and patch-size constraint tests.

## Metrics

- Patch validity rate.
- Patch application success rate.
- MusicXML valid after edit rate.
- Selection respect score.
- Constraint respect score.
- Preserve harmony score.
- Preserve melody score.
- Preserve rhythm score.
- Prompt alignment edit score.
- Over-editing penalty.
- Partial apply success rate.
- Undo/redo success rate.
- Explanation success rate.
- Average patch latency ms.

## Baseline

The default baseline is the mock-safe heuristic Score Editing Agent. Live LLM providers can be enabled with `SERA_LLM_PROVIDER=openai`, `deepseek`, or `qwen`, but missing API keys automatically fall back to mock so the benchmark remains runnable in local and CI environments.

## Failure Cases

Failures are written to `evaluation/results/score_editing_v07_failure_cases.json`. A trial is flagged when patch application fails or prompt-alignment score falls below the reporting threshold. Expected failure modes include overly broad operations, preserve-constraint violations, target-range drift, and requests that imply global meter/key changes from a local selection.

## Expected Results Table

| Metric | Mock baseline | LLM provider |
| --- | ---: | ---: |
| Patch validity rate |  |  |
| Patch application success rate |  |  |
| MusicXML valid after edit rate |  |  |
| Selection respect score |  |  |
| Constraint respect score |  |  |
| Prompt alignment edit score |  |  |
| Over-editing penalty |  |  |
| Partial apply success rate |  |  |
| Explanation success rate |  |  |
| Average patch latency ms |  |  |
