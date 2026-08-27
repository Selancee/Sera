# V0.96.2 Phrase-Level Melody

V0.96.2 addresses the remaining mechanical melody problem in the non-neural generator. Instead of selecting a short shape independently for each measure, the rule-based path now creates a 4-measure phrase or 8-measure period before emitting right-hand events.

The phrase melody engine combines:

- motif memory and transformation,
- phrase contour planning,
- harmonic target tones,
- tension/release planning,
- call-and-response role labels,
- cadence preparation,
- style-specific phrase strategies.

The final ScoreDocument is the integration test. `RuleBasedGenerator` computes `phrase_melody` before the measure loop and `_right_hand_events()` consumes its per-measure MIDI lists. The older expectation engine remains fallback only and `generation_metadata.hardcoded_shape_fallback_used` records whether that fallback was needed.

Style strategies are rule-based and transparent. Jazz favors guide tones and approach color; pop favors hook repetition with variation; classical favors antecedent/final period behavior; romantic favors a wider long-line arc; Chinese favors pentatonic open-space motion; cyberpunk favors short modal cells with controlled mutation.

This batch deliberately does not train a larger symbolic model. The phrase engine is a stronger baseline and a clearer target for later model training.
