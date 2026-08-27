"""Strict research pipeline for reliable language-guided score editing."""

__version__ = "0.1.0"


def __getattr__(name: str):
    """Load transaction classes lazily so domain tools remain importable alone."""

    if name in {"PatchTransaction", "TransactionResult"}:
        from sera_edit.execution.transaction import PatchTransaction, TransactionResult

        return {"PatchTransaction": PatchTransaction, "TransactionResult": TransactionResult}[name]
    raise AttributeError(name)


__all__ = ["PatchTransaction", "TransactionResult", "__version__"]
