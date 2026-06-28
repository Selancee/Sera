# Sera Project Instructions

Sera is an agent-assisted symbolic music generation app for natural-language prompts, editable scores, and reproducible MIR / AI music experiments.

Core pipeline:

User Prompt -> Prompt Understanding Agent -> Structured Music Intent -> Composition Planning Agent -> Measure-level Music Plan JSON -> Symbolic Music Generator -> Draft MusicXML / MIDI / ABC -> Music Rule Validator -> Revision Agent -> Final Score -> App Preview / Playback / Export.

Implementation priorities:

1. Keep the MVP runnable before adding heavy model dependencies.
2. Do not hardcode API keys.
3. Save prompts, plans, generated artifacts, validation reports, ratings, and baseline metadata to experiment logs.
4. Keep model training as a separate cloud-GPU-friendly pipeline.
5. Provide mock or stub modules for unfinished research features with clear TODO notes.
