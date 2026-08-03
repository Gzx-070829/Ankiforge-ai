"""Compatibility adapter from workbench review commands to the legacy session."""

from __future__ import annotations

from typing import Optional


_LEGACY_DECISIONS = {
    "keep": "looks_good",
    "needs_edit": "needs_revision",
    "discard": "skip_for_now",
}


class LegacyReviewSessionAdapter:
    """Expose only review operations needed by the application layer."""

    def __init__(self, session):
        required = (
            "review_workbench_snapshot",
            "set_candidate_review_decision",
            "replace_candidate_content",
            "restore_candidate_content",
            "keep_clean_candidates",
            "discard_blocking_candidates",
        )
        if any(not callable(getattr(session, name, None)) for name in required):
            raise TypeError("session does not satisfy the legacy review interface")
        self._session = session

    def snapshot(self):
        return self._session.review_workbench_snapshot()

    def set_decision(
        self,
        candidate_id: str,
        decision: Optional[str],
    ) -> None:
        legacy_decision = None if decision is None else _LEGACY_DECISIONS[decision]
        self._session.set_candidate_review_decision(
            candidate_id,
            legacy_decision,
        )

    def replace_content(self, candidate_id: str, front: str, back: str) -> None:
        self._session.replace_candidate_content(candidate_id, front, back)

    def restore_content(self, candidate_id: str) -> None:
        self._session.restore_candidate_content(candidate_id)

    def keep_clean(self) -> int:
        return self._session.keep_clean_candidates()

    def discard_blocking(self) -> int:
        return self._session.discard_blocking_candidates()

    def __repr__(self) -> str:
        return "LegacyReviewSessionAdapter(session_ready=True)"


__all__ = ["LegacyReviewSessionAdapter"]
