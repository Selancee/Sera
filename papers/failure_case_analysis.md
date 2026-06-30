# Failure Case Analysis

## Model-Based Collapse

Small-data full-score generation tends to collapse into the most frequent events: quarter durations, short stepwise motion, repeated XML tags, and weak phrase endings. This is musically audible as flat rhythm, narrow range, missing cadences, and little motivic development.

## V0.5 Mitigation

V0.5 splits representation into key, meter, position, rhythm, note, harmony, cadence, motif, and texture tokens. It also moves the model to local tasks and adds postprocess checks for excessive quarter notes, excessive same-direction steps, narrow range, missing cadence, incomplete bars, and out-of-range pitches.
