"""Transactional patch execution and reversible history."""

from __future__ import annotations

from typing import Any

__all__ = ["PatchTransaction", "TransactionResult"]


def __getattr__(name: str) -> Any:
    """Load transaction classes lazily to avoid validation/diff import cycles."""

    if name in __all__:
        from sera_edit.execution.transaction import PatchTransaction, TransactionResult

        return {"PatchTransaction": PatchTransaction, "TransactionResult": TransactionResult}[name]
    raise AttributeError(name)
