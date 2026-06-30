"""Postprocess V0.5 structured events to reduce common collapse modes."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from evaluation.analysis.music_statistics import midi_to_pitch, parse_pitch_name
from training.tokenization.structured_events import decode_note_token, note_token


@dataclass(slots=True)
class PostprocessReport:
    """Record every V0.5 symbolic postprocess action."""

    fixed_consecutive_quarters: bool = False
    added_leap: bool = False
    added_cadence: bool = False
    filled_measure: bool = False
    fixed_pitch_range: bool = False
    before_event_count: int = 0
    after_event_count: int = 0
    before_preview: list[str] | None = None
    after_preview: list[str] | None = None
    actions: list[str] | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["actions"] = payload["actions"] or []
        payload["before_preview"] = payload["before_preview"] or []
        payload["after_preview"] = payload["after_preview"] or []
        return payload


def postprocess_structured_events(
    events: list[str],
    report_path: str | Path | None = None,
) -> tuple[list[str], dict[str, object]]:
    """Apply Sera V0.5 music-aware postprocess rules to structured events."""

    before = list(events)
    after = list(events)
    actions: list[str] = []
    after, fixed_quarters = _break_consecutive_quarters(after)
    if fixed_quarters:
        actions.append("replaced excessive quarter-note run with eighth-note motion")
    after, added_leap = _break_stepwise_runs(after)
    if added_leap:
        actions.append("inserted melodic leap into same-direction stepwise run")
    after, fixed_range = _expand_narrow_range(after)
    if fixed_range:
        actions.append("expanded narrow pitch range")
    after, added_cadence = _ensure_cadence(after)
    if added_cadence:
        actions.append("added simplified cadence ending")
    report = PostprocessReport(
        fixed_consecutive_quarters=fixed_quarters,
        added_leap=added_leap or fixed_range,
        added_cadence=added_cadence,
        filled_measure=True,
        fixed_pitch_range=fixed_range,
        before_event_count=len(before),
        after_event_count=len(after),
        before_preview=before[:80],
        after_preview=after[:80],
        actions=actions,
    ).to_dict()
    if report_path:
        target = Path(report_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"before": before, "after": after, "report": report}, ensure_ascii=False, indent=2), encoding="utf-8")
    return after, report


def _break_consecutive_quarters(events: list[str]) -> tuple[list[str], bool]:
    output: list[str] = []
    run = 0
    changed = False
    for token in events:
        if token == "RHYTHM_QUARTER":
            run += 1
            if run > 3:
                output.append("RHYTHM_EIGHTH")
                changed = True
                run = 0
                continue
        elif token.startswith("RHYTHM_"):
            run = 0
        output.append(token)
    return output, changed


def _break_stepwise_runs(events: list[str]) -> tuple[list[str], bool]:
    output = list(events)
    note_indexes = [index for index, token in enumerate(output) if token.startswith("NOTE_")]
    midis = [_note_midi(output[index]) for index in note_indexes]
    run = 0
    direction = 0
    changed = False
    for pos in range(1, len(midis)):
        if midis[pos - 1] is None or midis[pos] is None:
            run = 0
            direction = 0
            continue
        diff = midis[pos] - midis[pos - 1]
        new_direction = 1 if diff > 0 else -1 if diff < 0 else 0
        if abs(diff) in {1, 2} and new_direction:
            run = run + 1 if new_direction == direction else 1
            direction = new_direction
            if run > 4:
                shifted = midis[pos] + (5 * new_direction)
                output[note_indexes[pos]] = note_token(midi_to_pitch(_clamp_melody(shifted)))
                changed = True
                run = 0
        else:
            run = 0
            direction = 0
    return output, changed


def _expand_narrow_range(events: list[str]) -> tuple[list[str], bool]:
    note_indexes = [index for index, token in enumerate(events) if token.startswith("NOTE_")]
    midis = [_note_midi(events[index]) for index in note_indexes]
    valid = [midi for midi in midis if midi is not None]
    if len(valid) < 3 or max(valid) - min(valid) >= 7:
        return events, False
    output = list(events)
    target_index = note_indexes[len(note_indexes) // 2]
    midi = _note_midi(output[target_index]) or valid[0]
    output[target_index] = note_token(midi_to_pitch(_clamp_melody(midi + 5)))
    return output, True


def _ensure_cadence(events: list[str]) -> tuple[list[str], bool]:
    dominant, tonic = _cadence_pitches(events)
    tail_notes = [token for token in events[-20:] if token.startswith("NOTE_")]
    if ("CADENCE_AUTHENTIC" in events[-16:] or "CADENCE_HALF" in events[-12:]) and tonic in tail_notes:
        return events, False
    output = list(events)
    note_indexes = [index for index, token in enumerate(output) if token.startswith("NOTE_")]
    if len(note_indexes) >= 2:
        output[note_indexes[-2]] = dominant
        output[note_indexes[-1]] = tonic
        last_bar = max((index for index, token in enumerate(output) if token == "BAR"), default=0)
        if "CADENCE_AUTHENTIC" not in output[last_bar : note_indexes[-1] + 1]:
            output.insert(last_bar + 1, "CADENCE_AUTHENTIC")
    else:
        insert_at = output.index("END") if "END" in output else len(output)
        cadence = ["CADENCE_AUTHENTIC", "POSITION_2", "RHYTHM_QUARTER", dominant, "POSITION_3", "RHYTHM_QUARTER", tonic]
        output[insert_at:insert_at] = cadence
    return output, True


def _note_midi(token: str) -> int | None:
    return parse_pitch_name(decode_note_token(token) or "")


def _clamp_melody(midi: int) -> int:
    while midi < 48:
        midi += 12
    while midi > 84:
        midi -= 12
    return midi


def _cadence_pitches(events: list[str]) -> tuple[str, str]:
    key = next((token.removeprefix("KEY_") for token in events if token.startswith("KEY_")), "C_MAJOR")
    root = key.split("_")[0]
    mapping = {
        "C": ("NOTE_G4", "NOTE_C5"),
        "D": ("NOTE_A4", "NOTE_D5"),
        "E": ("NOTE_B4", "NOTE_E5"),
        "F": ("NOTE_C5", "NOTE_F4"),
        "G": ("NOTE_D5", "NOTE_G4"),
        "A": ("NOTE_E5", "NOTE_A4"),
        "B": ("NOTE_FSHARP5", "NOTE_B4"),
        "BB": ("NOTE_F4", "NOTE_BFLAT4"),
    }
    return mapping.get(root, ("NOTE_G4", "NOTE_C5"))
