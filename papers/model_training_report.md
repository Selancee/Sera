# Model Training Report

## V0.4 Diagnosis

The V0.4 symbolic model was trained too close to full MusicXML generation. With a small dataset and a compact decoder, the model learned high-frequency token patterns rather than phrase-level musical behavior. The most common failure was quarter-note collapse: generated melodies overused continuous quarter durations, narrow pitch ranges, and stepwise motion. Cadential closure and motif development were weak because these concepts were not separated in the token representation.

## V0.5 Change

V0.5 introduces structured event tokens and multitask examples for melody fragment generation, motif variation, cadence generation, and rhythm rewrite. Training logs now keep task counts and task-loss history, and the main app treats the model as a local musicality assistant instead of a complete score generator.
