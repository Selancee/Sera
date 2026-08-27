"""V0.9 rhythm pattern engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.variation import variation_offset


DURATION_QUARTERS = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "sixteenth": 0.25,
    "dotted_half": 3.0,
    "dotted_quarter": 1.5,
    "dotted_eighth": 0.75,
}

PATTERNS: dict[str, list[tuple[str, ...]]] = {
    "4/4": [
        ("quarter", "quarter", "quarter", "quarter"),
        ("half", "quarter", "quarter"),
        ("quarter", "half", "quarter"),
        ("eighth", "eighth", "quarter", "quarter", "quarter"),
        ("quarter", "eighth", "eighth", "quarter", "quarter"),
        ("quarter", "quarter", "eighth", "eighth", "quarter"),
        ("dotted_quarter", "eighth", "quarter", "quarter"),
        ("quarter", "dotted_quarter", "eighth", "quarter"),
        ("eighth", "eighth", "eighth", "eighth", "quarter", "quarter"),
        ("quarter", "eighth", "eighth", "dotted_quarter", "eighth"),
        ("eighth", "quarter", "eighth", "quarter", "quarter"),
        ("rest_quarter", "quarter", "quarter", "quarter"),
        ("quarter", "rest_eighth", "eighth", "quarter", "quarter"),
        ("sixteenth", "sixteenth", "eighth", "quarter", "eighth", "eighth", "quarter"),
    ],
    "3/4": [
        ("quarter", "quarter", "quarter"),
        ("half", "quarter"),
        ("quarter", "half"),
        ("dotted_quarter", "eighth", "quarter"),
        ("quarter", "eighth", "eighth", "quarter"),
        ("eighth", "eighth", "quarter", "quarter"),
        ("quarter", "rest_quarter", "quarter"),
    ],
    "6/8": [
        ("dotted_quarter", "dotted_quarter"),
        ("eighth", "eighth", "eighth", "eighth", "eighth", "eighth"),
        ("quarter", "eighth", "quarter", "eighth"),
        ("dotted_quarter", "eighth", "eighth", "eighth"),
        ("eighth", "quarter", "eighth", "quarter"),
    ],
}


@dataclass(slots=True)
class RhythmEvent:
    label: str
    duration_quarters: float
    offset_quarters: float
    is_rest: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "duration_quarters": self.duration_quarters,
            "offset_quarters": self.offset_quarters,
            "is_rest": self.is_rest,
        }


class RhythmEngine:
    def generate(self, profile: GenerationProfile, measure_count: int) -> dict[str, Any]:
        candidates = self._candidate_patterns(profile)
        measures: list[dict[str, Any]] = []
        previous_name = ""
        repeat_count = 0
        for number in range(1, measure_count + 1):
            phrase_end = number % 4 == 0 or number == measure_count
            pattern = self._select_pattern(candidates, number, profile, phrase_end)
            if pattern == previous_name:
                repeat_count += 1
                if repeat_count > profile.max_repeated_rhythm_measures:
                    pattern = candidates[(candidates.index(pattern) + 1) % len(candidates)]
                    repeat_count = 1
            else:
                repeat_count = 1
            previous_name = pattern
            events = pattern_to_events(pattern)
            measures.append(
                {
                    "measure": number,
                    "pattern_id": pattern,
                    "events": [event.to_dict() for event in events],
                    "phrase_end": phrase_end,
                }
            )
        return {
            "engine": "rhythm_engine_v09",
            "meter": profile.meter,
            "rhythmic_density": profile.rhythmic_density,
            "syncopation": profile.syncopation,
            "style_parameters_applied": {
                "rhythmic_density": profile.rhythmic_density,
                "syncopation": profile.syncopation,
            },
            "unique_pattern_count": len({item["pattern_id"] for item in measures}),
            "measures": measures,
        }

    def _candidate_patterns(self, profile: GenerationProfile) -> list[str]:
        meter_patterns = PATTERNS.get(profile.meter, PATTERNS["4/4"])
        names = [pattern_name(pattern) for pattern in meter_patterns]
        if profile.difficulty == "beginner":
            names = [name for name in names if "sixteenth" not in name and "syncopated" not in name]
        if profile.rhythmic_density == "low":
            names = [name for name in names if "eighth" not in name or "dotted" in name][:4]
        elif profile.rhythmic_density == "high" and profile.difficulty != "beginner":
            names = names[3:] + names[:3]
        if profile.syncopation in {"medium", "high"} and profile.difficulty != "beginner":
            syncopated = [name for name in names if "eighth_quarter_eighth" in name or "rest_eighth" in name]
            names = syncopated + [name for name in names if name not in syncopated]
        if profile.rhythmic_density == "high" and profile.difficulty == "advanced":
            sixteenth = [name for name in names if "sixteenth" in name]
            names = sixteenth + [name for name in names if name not in sixteenth]
        if profile.requires_dotted_rhythm:
            dotted = [name for name in names if "dotted" in name]
            if profile.difficulty == "advanced":
                names = names[:2] + dotted + [name for name in names if name not in set(names[:2] + dotted)]
            else:
                names = dotted + [name for name in names if name not in dotted]
        return names or [pattern_name(PATTERNS.get(profile.meter, PATTERNS["4/4"])[0])]

    @staticmethod
    def _select_pattern(candidates: list[str], measure_number: int, profile: GenerationProfile, phrase_end: bool) -> str:
        offset = variation_offset(
            profile.variation_seed,
            len(candidates),
            f"rhythm:{profile.meter}:{profile.rhythmic_density}:{profile.syncopation}",
        )
        offset = (offset + profile.variation_index) % len(candidates) if candidates else 0
        if phrase_end:
            stable = [name for name in candidates if name.startswith(("half", "quarter_half", "dotted_quarter_dotted_quarter")) or name in {"quarter_quarter_quarter_quarter", "quarter_quarter_quarter"}]
            if stable:
                stable_offset = variation_offset(profile.variation_seed, len(stable), "rhythm:cadence")
                return stable[(measure_number // 4 + stable_offset + profile.variation_index) % len(stable)]
        return candidates[(measure_number - 1 + offset) % len(candidates)]


def pattern_name(pattern: tuple[str, ...]) -> str:
    return "_".join(pattern).replace("rest_quarter", "rest_quarter").replace("rest_eighth", "rest_eighth")


def pattern_to_events(pattern_id: str) -> list[RhythmEvent]:
    labels = pattern_id.split("_")
    merged: list[str] = []
    index = 0
    while index < len(labels):
      token = labels[index]
      if token in {"dotted", "rest"} and index + 1 < len(labels):
          merged.append(f"{token}_{labels[index + 1]}")
          index += 2
      else:
          merged.append(token)
          index += 1
    events: list[RhythmEvent] = []
    offset = 0.0
    for label in merged:
        clean = label.replace("rest_", "")
        duration = DURATION_QUARTERS.get(clean, 1.0)
        events.append(RhythmEvent(label=label, duration_quarters=duration, offset_quarters=offset, is_rest=label.startswith("rest_")))
        offset += duration
    return events
