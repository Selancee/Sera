# Sera V0.5 Composition Planning Prompt

Return only valid JSON for the Sera `CompositionPlan` schema. Keep the score
legal and playable before adding complexity.

Every section must include:

- `rhythmic_density`: `low`, `medium`, or `high`
- `melodic_contour`: `ascending`, `descending`, `arch`, `wave`, or `static`
- `cadence`: `none`, `half`, or `authentic`
- `motif_strategy`: `repeat`, `sequence_up`, `sequence_down`, `inversion`, `rhythmic_variation`, or `cadence`

Every measure plan must include:

- `rhythmic_density`
- `melodic_contour`
- `harmony` or `chord`
- `cadence`
- `interval_profile`
- `polyphony`
- `tension`
- `motif_id`
- `motif_strategy`

V0.5 generation contract:

1. The agent plans form, key, meter, harmony, density, contour, cadence, and texture.
2. Rule-based generation keeps MusicXML legal.
3. The small model only proposes local melody fragments, motif variation,
   cadence generation, or rhythm rewrites.
4. If a model output is invalid or unavailable, fall back to rule-based melody.
