# Training Data Notes

Sera V0.2 cloud training uses local generated examples plus an external MusicXML corpus.

## Default AutoDL Corpus

- Sera generated MusicXML: local `examples/scores` exports created by the app pipeline.
- ASAP dataset: `https://github.com/fosfrancesco/asap-dataset`, a GitHub corpus of aligned piano scores and performances with MusicXML and MIDI score files.

The AutoDL script clones ASAP into `/root/autodl-tmp/sera_data/asap-dataset` and builds a local JSONL dataset. It does not commit third-party scores or generated checkpoints to this repository by default.

## Larger Follow-Up Corpus

PDMX is a much larger public-domain MusicXML dataset with more than 250K scores. It is better suited for a later run with a larger budget. The current 50 RMB budget should be spent on a small reproducible proof run first.

TODO: add PDMX metadata filters for public-domain-only, piano-only, high-rating, and max-token-length subsets.
