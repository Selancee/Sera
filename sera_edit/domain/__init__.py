"""SeraEdit domain contracts."""

from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.domain.score_patch import PatchOperation, ScorePatch
from sera_edit.domain.score_scope import EventContext, ScoreScope, iter_event_contexts

__all__ = [
    "EventContext",
    "PatchOperation",
    "ScorePatch",
    "ScoreScope",
    "iter_event_contexts",
    "score_fingerprint",
]
