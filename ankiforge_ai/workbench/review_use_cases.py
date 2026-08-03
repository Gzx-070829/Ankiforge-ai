"""Narrow, validated review operations independent of Qt and legacy models."""

from __future__ import annotations

import re
from typing import Optional, Protocol


MAX_REVIEW_CARD_TEXT_CHARS = 12_000
_SAFE_CANDIDATE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_DECISIONS = frozenset({"keep", "discard", "needs_edit"})
_REQUIRED_METHODS = (
    "snapshot",
    "set_decision",
    "replace_content",
    "restore_content",
    "keep_clean",
    "discard_blocking",
)


class ReviewSessionPort(Protocol):
    def snapshot(self):
        pass

    def set_decision(
        self,
        candidate_id: str,
        decision: Optional[str],
    ) -> None:
        pass

    def replace_content(self, candidate_id: str, front: str, back: str) -> None:
        pass

    def restore_content(self, candidate_id: str) -> None:
        pass

    def keep_clean(self) -> int:
        pass

    def discard_blocking(self) -> int:
        pass


def _validate_candidate_id(candidate_id: object) -> None:
    if not isinstance(candidate_id, str) or not _SAFE_CANDIDATE_ID.fullmatch(
        candidate_id
    ):
        raise ValueError("candidate_id must be a safe bounded identifier")


def _validate_bulk_count(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"review port returned an invalid {name} count")
    return value


class ReviewUseCases:
    """Validate review commands before delegating to an in-memory port."""

    def __init__(self, port: ReviewSessionPort):
        if any(not callable(getattr(port, name, None)) for name in _REQUIRED_METHODS):
            raise TypeError("port does not satisfy the review session interface")
        self._port = port

    def snapshot(self):
        return self._port.snapshot()

    def set_decision(
        self,
        candidate_id: str,
        decision: Optional[str],
    ) -> None:
        _validate_candidate_id(candidate_id)
        if decision is not None and decision not in _DECISIONS:
            raise ValueError("decision must be keep, discard, needs_edit, or None")
        self._port.set_decision(candidate_id, decision)

    def replace_content(self, candidate_id: str, front: str, back: str) -> None:
        _validate_candidate_id(candidate_id)
        if not isinstance(front, str) or not isinstance(back, str):
            raise ValueError("front and back must be strings")
        if (
            len(front) > MAX_REVIEW_CARD_TEXT_CHARS
            or len(back) > MAX_REVIEW_CARD_TEXT_CHARS
        ):
            raise ValueError("edited card text exceeds the local safety limit")
        self._port.replace_content(candidate_id, front, back)

    def restore_content(self, candidate_id: str) -> None:
        _validate_candidate_id(candidate_id)
        self._port.restore_content(candidate_id)

    def keep_clean(self) -> int:
        return _validate_bulk_count(self._port.keep_clean(), "kept")

    def discard_blocking(self) -> int:
        return _validate_bulk_count(
            self._port.discard_blocking(),
            "discarded",
        )

    def __repr__(self) -> str:
        return "ReviewUseCases(port_ready=True)"


__all__ = [
    "MAX_REVIEW_CARD_TEXT_CHARS",
    "ReviewSessionPort",
    "ReviewUseCases",
]
