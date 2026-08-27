# V0.96 Style Harmony Profile

The harmony system now follows:

```text
style -> harmony_profile -> progression -> voicing -> voice_leading_validation
```

Jazz profiles expose extensions and substitution; Chinese profiles expose pentatonic verticalization, open fifths, quartal sonorities, and pedal tones; classical profiles penalize parallel fifths/octaves; pop profiles prefer common loop vocabulary; romantic profiles allow secondary dominants and chromatic approach; electronic/cyberpunk profiles use modal cells, pedal point, ostinato bass, and sus/quartal clusters.

V0.96.1 makes this profile chain executable in the final score. The harmony profile now selects the actual progression used by the generator; old variation logic may no longer overwrite a jazz profile with generic I-vi-ii-V cells. The voicing engine's MIDI pitches are converted into final left-hand events, and `actual_harmony_style_report` compares the generated notes against the declared style.
