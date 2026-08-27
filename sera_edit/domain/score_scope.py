"""Deterministic target and protected score-scope matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Iterable, Iterator


STAFF_ALIASES = {
    "1": "right_hand",
    "right": "right_hand",
    "right_hand": "right_hand",
    "upper": "right_hand",
    "2": "left_hand",
    "left": "left_hand",
    "left_hand": "left_hand",
    "lower": "left_hand",
}


def normalize_staff(value: object) -> str:
    """Return the canonical staff label used by ScoreDocument."""

    clean = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return STAFF_ALIASES.get(clean, clean)


def _fraction(value: object) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        return Fraction(str(value))
    return Fraction(str(value or "0"))


@dataclass(frozen=True, slots=True)
class EventContext:
    """One canonical event plus its structural location."""

    measure: int
    measure_id: str
    part_id: str
    staff: str
    voice: int
    event_id: str
    offset: Fraction
    event: dict[str, Any]

    def location(self) -> dict[str, Any]:
        """Return a JSON-serializable structural locator."""

        return {
            "measure": self.measure,
            "measure_id": self.measure_id,
            "part_id": self.part_id,
            "staff": self.staff,
            "voice": self.voice,
            "event_id": self.event_id,
            "offset": str(self.offset),
        }


def iter_event_contexts(score_document: dict[str, Any]) -> Iterator[EventContext]:
    """Yield events in deterministic score order."""

    default_part = str((score_document.get("parts") or [{}])[0].get("part_id", "piano"))
    for measure in sorted(score_document.get("measures") or [], key=lambda item: int(item.get("number", 0))):
        number = int(measure.get("number", 0))
        measure_id = str(measure.get("measure_id", f"m{number}"))
        events = sorted(
            measure.get("events") or [],
            key=lambda item: (
                _fraction(item.get("offset", 0)),
                normalize_staff(item.get("staff", "right_hand")),
                int(item.get("voice", 1) or 1),
                str(item.get("event_id", "")),
            ),
        )
        for event in events:
            yield EventContext(
                measure=number,
                measure_id=measure_id,
                part_id=str(event.get("part_id", default_part)),
                staff=normalize_staff(event.get("staff", "right_hand")),
                voice=int(event.get("voice", 1) or 1),
                event_id=str(event.get("event_id", "")),
                offset=_fraction(event.get("offset", 0)),
                event=event,
            )


@dataclass(frozen=True, slots=True)
class ScoreScope:
    """A deterministic selection over ScoreDocument structural locations."""

    measures: frozenset[int] = field(default_factory=frozenset)
    parts: frozenset[str] = field(default_factory=frozenset)
    staffs: frozenset[str] = field(default_factory=frozenset)
    voices: frozenset[int] = field(default_factory=frozenset)
    event_ids: frozenset[str] = field(default_factory=frozenset)
    exclude_measures: frozenset[int] = field(default_factory=frozenset)
    exclude_event_ids: frozenset[str] = field(default_factory=frozenset)
    time_range: tuple[Fraction, Fraction] | None = None
    whole_score: bool = False

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ScoreScope":
        """Parse a JSON score scope without silently accepting bad ranges."""

        data = dict(payload or {})
        time_range = data.get("time_range")
        parsed_time: tuple[Fraction, Fraction] | None = None
        if time_range is not None:
            if isinstance(time_range, dict):
                start, end = time_range.get("start"), time_range.get("end")
            elif isinstance(time_range, (list, tuple)) and len(time_range) == 2:
                start, end = time_range
            else:
                raise ValueError("time_range must be {start,end} or a two-item array")
            parsed_time = (_fraction(start), _fraction(end))
            if parsed_time[0] > parsed_time[1]:
                raise ValueError("time_range start must be <= end")
        measures = frozenset(int(value) for value in data.get("measures") or [])
        voices = frozenset(int(value) for value in data.get("voices") or [])
        if any(value < 1 for value in measures):
            raise ValueError("scope measures must be positive")
        if any(value < 1 for value in voices):
            raise ValueError("scope voices must be positive")
        return cls(
            measures=measures,
            parts=frozenset(str(value) for value in data.get("parts") or []),
            staffs=frozenset(normalize_staff(value) for value in data.get("staffs") or []),
            voices=voices,
            event_ids=frozenset(str(value) for value in data.get("event_ids") or []),
            exclude_measures=frozenset(int(value) for value in data.get("exclude_measures") or []),
            exclude_event_ids=frozenset(str(value) for value in data.get("exclude_event_ids") or []),
            time_range=parsed_time,
            whole_score=bool(data.get("whole_score", False)),
        )

    @property
    def empty(self) -> bool:
        """Return whether the scope has no positive selector."""

        return not (
            self.whole_score
            or self.measures
            or self.parts
            or self.staffs
            or self.voices
            or self.event_ids
            or self.time_range is not None
        )

    def contains(self, context: EventContext, *, empty_matches: bool = False) -> bool:
        """Return whether an event context is inside this scope."""

        if context.measure in self.exclude_measures or context.event_id in self.exclude_event_ids:
            return False
        if self.empty:
            return empty_matches
        if self.event_ids and context.event_id not in self.event_ids:
            return False
        if self.measures and context.measure not in self.measures:
            return False
        if self.parts and context.part_id not in self.parts:
            return False
        if self.staffs and context.staff not in self.staffs:
            return False
        if self.voices and context.voice not in self.voices:
            return False
        if self.time_range is not None and not (self.time_range[0] <= context.offset < self.time_range[1]):
            return False
        return True

    def select(self, score_document: dict[str, Any], *, empty_matches: bool = False) -> list[EventContext]:
        """Return all matching score events."""

        return [context for context in iter_event_contexts(score_document) if self.contains(context, empty_matches=empty_matches)]

    def as_dict(self) -> dict[str, Any]:
        """Return the versioned JSON representation."""

        return {
            "measures": sorted(self.measures),
            "parts": sorted(self.parts),
            "staffs": sorted(self.staffs),
            "voices": sorted(self.voices),
            "event_ids": sorted(self.event_ids),
            "exclude_measures": sorted(self.exclude_measures),
            "exclude_event_ids": sorted(self.exclude_event_ids),
            "time_range": None
            if self.time_range is None
            else {"start": str(self.time_range[0]), "end": str(self.time_range[1])},
            "whole_score": self.whole_score,
        }


def scope_for_contexts(contexts: Iterable[EventContext]) -> ScoreScope:
    """Build an event-ID scope from known event contexts."""

    return ScoreScope(event_ids=frozenset(context.event_id for context in contexts))
