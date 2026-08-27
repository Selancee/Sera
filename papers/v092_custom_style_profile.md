# V0.92 Custom Style Profile

V0.92 preserves custom prompt style words instead of forcing them into a fixed classical/pop/romantic set. Prompts such as cyberpunk, anime, cinematic, new age, and game soundtrack produce `custom_style_tags`, a `base_style`, and a structured `style_profile`.

The profile maps user language to executable controls:

- rhythm density and syncopation for `rhythm_engine`
- texture for `texture_engine`
- accompaniment style for `accompaniment_engine`
- harmony flavor for `harmony_engine`
- cadence strength for `cadence_engine`
- dynamic contrast for `dynamics_engine`

For example, cyberpunk maps to electronic base style, ostinato texture, repeating bass accompaniment, minor modal harmony, medium cadence strength, middle-low register bias, and high dynamic contrast. The mapping is rule-based and transparent; it is not yet a trained style-conditioned generator.
