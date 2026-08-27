"""Resolve an instruction's explicit score location inside the host selection.

The notation host owns the coarse selection.  Natural-language instructions
may name a smaller measure or staff inside that selection.  This module only
narrows the host selection; it never grants access to an unselected location.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sera_edit.domain.score_scope import ScoreScope, iter_event_contexts, normalize_staff


_RANGE_SEPARATORS = r"(?:-|\u2013|\u2014|~|to|through)"


@dataclass(frozen=True, slots=True)
class InstructionScopeResolution:
    """One deterministic host-selection/instruction-scope resolution."""

    requested_scope: ScoreScope
    effective_scope: ScoreScope | None
    explicit_measures: tuple[int, ...] = ()
    explicit_staffs: tuple[str, ...] = ()
    excluded_host_measures: tuple[int, ...] = ()
    excluded_host_staffs: tuple[str, ...] = ()
    status: str = "requested_scope"
    reason: str | None = None

    @property
    def valid(self) -> bool:
        return self.effective_scope is not None

    def provenance(self) -> dict[str, Any]:
        return {
            "scope_resolution": self.status,
            "requested_target_scope": self.requested_scope.as_dict(),
            "explicit_instruction_scope": {
                "measures": list(self.explicit_measures),
                "staffs": list(self.explicit_staffs),
            },
            "excluded_host_scope": {
                "measures": list(self.excluded_host_measures),
                "staffs": list(self.excluded_host_staffs),
            },
        }


def explicit_instruction_measures(instruction: str) -> tuple[int, ...]:
    """Extract only measure numbers that are explicitly labelled as measures."""

    text = instruction.strip().lower()
    measures: set[int] = set()
    range_patterns = (
        rf"\bmeasures?\s+(\d+)\s*{_RANGE_SEPARATORS}\s*(?:measure\s*)?(\d+)\b",
        rf"\u7b2c?\s*(\d+)\s*(?:\u81f3|\u5230|-|\u2013|\u2014|~)\s*\u7b2c?\s*(\d+)\s*\u5c0f\u8282",
    )
    for pattern in range_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            start, end = int(match.group(1)), int(match.group(2))
            if start > 0 and end > 0:
                low, high = sorted((start, end))
                measures.update(range(low, high + 1))
    singular_patterns = (
        r"\bmeasure\s+(\d+)\b",
        r"\u7b2c\s*(\d+)\s*\u5c0f\u8282",
    )
    for pattern in singular_patterns:
        measures.update(
            int(match.group(1))
            for match in re.finditer(pattern, text, flags=re.IGNORECASE)
            if int(match.group(1)) > 0
        )
    return tuple(sorted(measures))


def explicit_instruction_staffs(instruction: str) -> tuple[str, ...]:
    """Extract an explicitly named notation staff without parsing voice targets."""

    text = instruction.strip().lower()
    staffs: set[str] = set()
    patterns = {
        "right_hand": (
            r"\bstaff\s*1\b",
            r"\b(?:upper|top) staff\b",
            r"\bright[ -]?hand\b",
            r"\u7b2c\s*(?:1|\u4e00)\s*\u8c31\u8868",
            r"\u53f3\u624b",
        ),
        "left_hand": (
            r"\bstaff\s*2\b",
            r"\b(?:lower|bottom) staff\b",
            r"\bleft[ -]?hand\b",
            r"\u7b2c\s*(?:2|\u4e8c)\s*\u8c31\u8868",
            r"\u5de6\u624b",
        ),
    }
    for staff, candidates in patterns.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in candidates):
            staffs.add(staff)
    return tuple(sorted(staffs))


def resolve_instruction_target_scope(
    score_document: dict[str, Any],
    instruction: str,
    target_scope_payload: dict[str, Any],
    *,
    preserve_global_scope: bool = False,
) -> InstructionScopeResolution:
    """Intersect explicit instruction locations with the host-owned selection.

    ``preserve_global_scope`` is reserved for server-recognized global score
    properties such as key and time signatures.  It prevents a global edit
    from being accidentally converted into a local event edit.
    """

    requested = ScoreScope.from_dict(target_scope_payload)
    explicit_measures = explicit_instruction_measures(instruction)
    explicit_staffs = explicit_instruction_staffs(instruction)
    if preserve_global_scope or (not explicit_measures and not explicit_staffs):
        return InstructionScopeResolution(
            requested_scope=requested,
            effective_scope=requested,
            explicit_measures=explicit_measures,
            explicit_staffs=explicit_staffs,
        )

    measure_set = frozenset(explicit_measures)
    staff_set = frozenset(normalize_staff(value) for value in explicit_staffs)
    requested_contexts = requested.select(score_document)
    requested_context_by_id = {context.event_id: context for context in requested_contexts}

    if measure_set and requested.measures and not measure_set.issubset(requested.measures):
        missing = sorted(measure_set - requested.measures)
        return InstructionScopeResolution(
            requested_scope=requested,
            effective_scope=None,
            explicit_measures=explicit_measures,
            explicit_staffs=explicit_staffs,
            status="instruction_scope_outside_host_selection",
            reason=f"Instruction names unselected measure(s): {missing}.",
        )
    if staff_set and requested.staffs and not staff_set.issubset(requested.staffs):
        missing = sorted(staff_set - requested.staffs)
        return InstructionScopeResolution(
            requested_scope=requested,
            effective_scope=None,
            explicit_measures=explicit_measures,
            explicit_staffs=explicit_staffs,
            status="instruction_scope_outside_host_selection",
            reason=f"Instruction names unselected staff(s): {missing}.",
        )

    filtered_event_ids = requested.event_ids
    if requested.event_ids:
        filtered_event_ids = frozenset(
            event_id
            for event_id, context in requested_context_by_id.items()
            if (not measure_set or context.measure in measure_set)
            and (not staff_set or context.staff in staff_set)
        )
        if not filtered_event_ids:
            return InstructionScopeResolution(
                requested_scope=requested,
                effective_scope=None,
                explicit_measures=explicit_measures,
                explicit_staffs=explicit_staffs,
                status="instruction_scope_outside_host_selection",
                reason="The instruction location contains no event in the current host selection.",
            )

    effective = ScoreScope(
        measures=measure_set or requested.measures,
        parts=requested.parts,
        staffs=staff_set or requested.staffs,
        voices=requested.voices,
        event_ids=filtered_event_ids,
        exclude_measures=requested.exclude_measures,
        exclude_event_ids=requested.exclude_event_ids,
        time_range=requested.time_range,
        whole_score=False if (measure_set or staff_set) else requested.whole_score,
    )
    if not effective.select(score_document):
        return InstructionScopeResolution(
            requested_scope=requested,
            effective_scope=None,
            explicit_measures=explicit_measures,
            explicit_staffs=explicit_staffs,
            status="instruction_scope_outside_host_selection",
            reason="The instruction location contains no editable event in the current host selection.",
        )

    excluded_measures = tuple(sorted(requested.measures - effective.measures))
    excluded_staffs = tuple(sorted(requested.staffs - effective.staffs))
    changed = effective.as_dict() != requested.as_dict()
    return InstructionScopeResolution(
        requested_scope=requested,
        effective_scope=effective,
        explicit_measures=explicit_measures,
        explicit_staffs=explicit_staffs,
        excluded_host_measures=excluded_measures,
        excluded_host_staffs=excluded_staffs,
        status="narrowed_to_explicit_instruction_scope" if changed else "requested_scope",
    )
