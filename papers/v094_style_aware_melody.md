# V0.94 Style-Aware Melody

V0.94 introduced a style-aware melodic profile before V0.95's metadata and melody-line work. Cyberpunk, anime, Chinese, romantic, and default profiles map prompt/style tags to pitch vocabulary, contour policy, interval policy, and motif source. The rule-based generator uses this profile for right-hand melody material before MusicXML assembly.

V0.95 builds on this by validating the extracted primary melody line across measure boundaries. Style remains part of the grammar context, but left-hand accompaniment is no longer mixed into melodic interval diagnostics.
