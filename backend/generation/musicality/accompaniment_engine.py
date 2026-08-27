"""Left-hand accompaniment engine for V0.9."""

from __future__ import annotations

from typing import Any

from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.harmony_profile import build_harmony_profile
from backend.generation.musicality.pitch_spelling import midi_to_pitch_name
from backend.generation.musicality.voicing_engine import voice_chord


SEMITONE_TO_PITCH = {
    0: ("C", ""),
    1: ("C", "#"),
    2: ("D", ""),
    3: ("E", "b"),
    4: ("E", ""),
    5: ("F", ""),
    6: ("F", "#"),
    7: ("G", ""),
    8: ("A", "b"),
    9: ("A", ""),
    10: ("B", "b"),
    11: ("B", ""),
}


CHORD_PITCHES = {
    "I": ["C3", "E3", "G3"],
    "i": ["A2", "C3", "E3"],
    "IV": ["F2", "C3", "F3"],
    "iv": ["D3", "F3", "A3"],
    "V": ["G2", "D3", "G3"],
    "vi": ["A2", "E3", "A3"],
    "VI": ["F2", "C3", "F3"],
    "III": ["E3", "G3", "B3"],
    "VII": ["G2", "D3", "G3"],
    "ii": ["D3", "F3", "A3"],
}


class AccompanimentEngine:
    def choose_style(self, profile: GenerationProfile) -> str:
        if profile.accompaniment_style:
            return profile.accompaniment_style
        if profile.difficulty == "beginner":
            return "sparse_beginner_bass"
        if profile.texture == "waltz" or profile.meter == "3/4":
            return "waltz_bass"
        if profile.base_style == "romantic" or profile.style == "romantic":
            return "arpeggiated_chords"
        if profile.base_style == "chinese" or profile.style == "chinese":
            return "simple_pedal_point"
        return "bass_chord"

    def generate(self, profile: GenerationProfile, chords: list[str]) -> dict[str, Any]:
        style = self.choose_style(profile)
        mode = "minor" if "minor" in profile.key.lower() else "major"
        harmony_profile = build_harmony_profile(
            {
                **dict(profile.style_profile or {}),
                "style": profile.style,
                "base_style": profile.base_style,
                "custom_style_tags": list(profile.custom_style_tags or []),
            },
            key=profile.key,
            mode=mode,
            difficulty=profile.difficulty,
        )
        measures = []
        voicings = []
        previous = None
        fallback_count = 0
        actual_voicing_pitches_by_measure: dict[int, list[str]] = {}
        for chord in chords:
            voicing = voice_chord(chord, harmony_profile, register="left_hand", role="accompaniment", previous_voicing=previous)
            previous = list(voicing.get("voicing", []))
            voicings.append(voicing)
        for number, (chord, voicing) in enumerate(zip(chords, voicings, strict=False), start=1):
            measure = self.generate_measure(profile, number, chord, style, voicing=voicing)
            if measure.get("voicing_source") == "static_chord_fallback":
                fallback_count += 1
            actual_voicing_pitches_by_measure[number] = list(measure.get("actual_voicing_pitches", []))
            measures.append(measure)
        return {
            "engine": "accompaniment_engine_v09",
            "style": style,
            "style_parameters_applied": {"accompaniment_style": profile.accompaniment_style},
            "voicing_report": {"voicings": voicings, "harmony_profile_style": harmony_profile.get("style")},
            "voicing_source": "static_chord_fallback" if fallback_count == len(chords) else "voicing_engine",
            "fallback_count": fallback_count,
            "actual_voicing_pitches_by_measure": actual_voicing_pitches_by_measure,
            "measures": measures,
        }

    def generate_measure(
        self,
        profile: GenerationProfile,
        measure_number: int,
        chord: str,
        style: str | None = None,
        voicing: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        style = style or self.choose_style(profile)
        mode = "minor" if "minor" in profile.key.lower() else "major"
        voicing_midis = [int(item) for item in (voicing or {}).get("voicing", []) if isinstance(item, int)]
        voicing_source = "voicing_engine" if voicing_midis else "static_chord_fallback"
        pitches = [midi_to_pitch_name(item, profile.key, mode) for item in voicing_midis] if voicing_midis else CHORD_PITCHES.get(chord.replace("7", "").replace("maj", ""), CHORD_PITCHES["I"])
        pitches = _dedupe_pitches(pitches)
        if len(pitches) < 3:
            pitches = (pitches + CHORD_PITCHES.get(chord.replace("7", "").replace("maj", ""), CHORD_PITCHES["I"]))[:3]
            pitches = _dedupe_pitches(pitches)
        capacity = 3.0 if profile.meter == "3/4" else 3.0 if profile.meter == "6/8" else 4.0
        events: list[dict[str, Any]]
        if style == "block_chords":
            events = [{"pitches": pitches, "duration_quarters": capacity, "offset_quarters": 0.0}]
        elif style == "alberti_bass":
            pattern = [pitches[0], pitches[2], pitches[1], pitches[2]]
            events = _repeating(pattern, 0.5, capacity)
        elif style in {"arpeggiated_chords", "flowing_arpeggio"}:
            events = _repeating([pitches[0], pitches[1], pitches[2], pitches[1]], 0.5, capacity)
        elif style in {"repeating_bass", "repeating_pattern"}:
            events = _repeating([pitches[0], pitches[0], pitches[2], pitches[0]], 0.5, capacity)
        elif style == "waltz_bass":
            events = [
                {"pitches": [pitches[0]], "duration_quarters": 1.0, "offset_quarters": 0.0},
                {"pitches": pitches[1:], "duration_quarters": 1.0, "offset_quarters": 1.0},
                {"pitches": pitches[1:], "duration_quarters": 1.0, "offset_quarters": 2.0},
            ]
        elif style in {"simple_pedal_point", "open_fifth_pedal"}:
            fifth_index = 1 if len(pitches) > 1 else 0
            events = _repeating([pitches[0], pitches[fifth_index]], 1.0, capacity)
        elif style == "sparse_beginner_bass":
            events = [
                {"pitches": [pitches[0]], "duration_quarters": 2.0, "offset_quarters": 0.0},
                {"pitches": [pitches[1]], "duration_quarters": max(1.0, capacity - 2.0), "offset_quarters": 2.0},
            ]
        else:
            events = [
                {"pitches": [pitches[0]], "duration_quarters": 1.0, "offset_quarters": 0.0},
                {"pitches": pitches[1:], "duration_quarters": 1.0, "offset_quarters": 1.0},
                {"pitches": [pitches[0]], "duration_quarters": 1.0, "offset_quarters": 2.0},
                {"pitches": pitches[1:], "duration_quarters": max(0.5, capacity - 3.0), "offset_quarters": 3.0},
            ]
        return {
            "measure": measure_number,
            "style": style,
            "chord": chord,
            "events": events,
            "voicing_source": voicing_source,
            "actual_voicing_pitches": pitches,
            "voicing": voicing or {},
        }


def _repeating(pattern: list[str], duration: float, capacity: float) -> list[dict[str, Any]]:
    events = []
    offset = 0.0
    index = 0
    while offset < capacity - 0.001:
        events.append({"pitches": [pattern[index % len(pattern)]], "duration_quarters": min(duration, capacity - offset), "offset_quarters": offset})
        offset += duration
        index += 1
    return events


def _dedupe_pitches(pitches: list[str]) -> list[str]:
    out: list[str] = []
    for pitch in pitches:
        if pitch not in out:
            out.append(pitch)
    return out
