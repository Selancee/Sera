# System Description Draft

## Overview

Sera is an agentic text-to-score composition system designed for editable symbolic music generation and reproducible MIR / AI music experiments. The system converts a natural-language prompt into a structured composition plan, generates a playable MusicXML score, validates notation quality, optionally revises the plan, and saves all artifacts in an experiment directory.

## Agent Pipeline

The Prompt Understanding Agent parses user prompts into a stable JSON intent. The intent includes title, style, mood, instrumentation, key, meter, tempo, length, form, texture, difficulty, harmony plan, section plan, and revision goals. Missing prompt fields are completed by deterministic defaults. If an OpenAI-compatible LLM provider is configured, Sera merges only schema-safe JSON fields; otherwise it falls back to local rules.

The Composition Planning Agent expands the intent into a measure-level plan. Each measure receives a section label, chord, harmonic function, rhythm profile, density, cadence, motif degrees, texture, and description. This intermediate plan is intended to be inspectable by researchers and editable in future user studies.

## Symbolic Generation

The V0.2 generator is rule-based and MusicXML-first. It supports piano single-line sketches and simplified two-staff piano textures, 4/4, 3/4, and 6/8 meters, major and minor keys, 8, 16, and 32 measure forms, basic harmonic progressions, repeated motifs, motivic variation, controlled range, and cadential closure.

TODO: Replace or augment the rule-based generator with a trained symbolic model once a token vocabulary and cloud GPU training pipeline are validated.

## Validation and Revision

The MusicXML validator checks XML parsing, music21 parsing when available, plan length match, per-staff/per-voice measure completeness, pitch range, empty measures, MIDI export, and PDF export. The Revision Agent repairs empty or incomplete measure plans and applies user feedback such as "more melancholic", "Chopin-like", "change to triple meter", "lower difficulty", "faster", and "more flowing left hand".

## Research Workbench

The frontend is a React/Vite workbench with prompt entry, parameter shortcuts, Agent plan visualization, score preview, MIDI playback/download, revision input, validation report, export controls, and experiment history. If full engraving is unavailable, the UI presents a simplified score preview and MusicXML/export links.

## Reproducibility

Each run writes an independent folder under `experiments/` containing `prompt.txt`, `plan.json`, `generated.musicxml`, `generated.mid`, `generated.pdf`, `validation_report.json`, `revision_history.json`, `metadata.json`, and `experiment_log.json`. This structure is intended to support paper figures, evaluation tables, and post-hoc failure analysis.
