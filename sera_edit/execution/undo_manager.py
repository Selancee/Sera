"""Patch-level undo/redo using immutable transaction snapshots."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class UndoManager:
    """Hold patch history independently from legacy operation history."""

    done: list[dict[str, Any]] = field(default_factory=list)
    undone: list[dict[str, Any]] = field(default_factory=list)

    def record(self, entry: dict[str, Any]) -> None:
        self.done.append(copy.deepcopy(entry))
        self.undone.clear()

    def undo(self, score_document: dict[str, Any]) -> dict[str, Any]:
        if not self.done:
            return copy.deepcopy(score_document)
        entry = self.done.pop()
        self.undone.append(entry)
        return copy.deepcopy(entry["before_score_document"])

    def redo(self, score_document: dict[str, Any]) -> dict[str, Any]:
        if not self.undone:
            return copy.deepcopy(score_document)
        entry = self.undone.pop()
        self.done.append(entry)
        return copy.deepcopy(entry["after_score_document"])

    def as_dict(self) -> dict[str, Any]:
        return {"done": copy.deepcopy(self.done), "undone": copy.deepcopy(self.undone)}
