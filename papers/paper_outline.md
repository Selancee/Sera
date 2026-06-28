# Sera Paper Outline

## Working Title

Sera: An Agentic Text-to-Score Composition System with Reproducible Symbolic Evaluation

## Abstract

TODO: Summarize the agent planning loop, MusicXML-first generation, validator-guided revision, and reproducible experiment logging.

## 1. Introduction

- Motivation: text-to-music systems often optimize audio generation while under-serving editable notation, validation, and reproducibility.
- Research gap: prompt-to-score workflows need structured planning, symbolic constraints, and experiment records suitable for MIR / AI music research.
- Contributions:
  1. A modular Agentic prompt-to-score app.
  2. A stable JSON composition planning interface.
  3. A MusicXML validation and revision loop.
  4. A batch evaluation workflow and experiment log format.

## 2. Related Work

- Text-conditioned music generation.
- Symbolic music generation and MusicXML/MIDI representations.
- Agentic planning and controllable creative systems.
- MIR evaluation and human-centered music AI studies.

## 3. System

- Prompt Understanding Agent.
- Composition Planning Agent.
- Rule-based symbolic generator.
- MusicXML validator.
- Revision Agent.
- Research workbench UI.
- Experiment logging and exports.

## 4. Method

- Structured intent schema.
- Measure-level planning representation.
- Deterministic baseline generation.
- Validator-guided repair.
- TODO: future model-backed generator and LoRA symbolic training.

## 5. Evaluation

- Prompt set: 20 prompts covering classical, romantic, jazz, pop, Chinese pentatonic, electronic ambient, beginner piano, triple meter, fast lively, and sad adagio styles.
- Automatic metrics: MusicXML validity, MIDI/PDF export success, bar completeness, pitch range validity, empty measure rate, rule prompt adherence, revision success.
- Human evaluation: readability, playability, prompt fit, musical coherence, and editability.

## 6. Results

TODO: Report evaluation table, examples, validator failures, revision outcomes, and representative score excerpts.

## 7. Discussion

- Benefits of schema-constrained planning.
- Limits of rule-based generation.
- Tradeoffs between valid notation and expressive complexity.
- Failure cases and usability observations.

## 8. Conclusion

TODO: Summarize findings and future work toward neural symbolic generation, richer notation rendering, and controlled human studies.
