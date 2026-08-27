# V0.95 Melody-Line Extraction

V0.95 separates melody diagnostics from playback events. Playback events are a mixed performance stream containing right hand and left hand notes sorted by time. That stream is useful for MIDI preview, but it is not a valid melodic line for interval diagnostics.

The melody-line extractor groups ScoreDocument events by staff and voice. For piano scores it prefers `right_hand` voice 1 as the primary melody, records other right-hand voices as secondary candidates, and excludes `left_hand` lines as accompaniment. The generated metadata includes `melody_line_report` with primary melody events, pitch list, measure range, phrase ranges, excluded lines, and warnings.

Frontend diagnostics state that melodic interval reports come from the extracted primary melody line rather than mixed playback events.
## V0.96 Extension

V0.96 keeps the V0.95 primary melody-line extractor as the source for melody diagnostics. The extracted right-hand voice 1 line is now passed into `melody_expectation_validator`, which adds leap reversal, mean regression, gap fill, tonal anchoring, closure, and dissonance-handling metrics without replacing the existing melody-line report.
