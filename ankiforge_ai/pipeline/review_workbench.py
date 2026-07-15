"""Immutable, local-only review workbench state and operations."""

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Iterable

from .card_quality import CardQualityResult, evaluate_card_quality


class ReviewDecision(str, Enum):
    PENDING = "pending"
    KEPT = "kept"
    DISCARDED = "discarded"


@dataclass(frozen=True, repr=False)
class ReviewCandidate:
    candidate_id: str
    front: str = field(repr=False)
    back: str = field(repr=False)
    source: str = field(repr=False)
    original_front: str = field(repr=False)
    original_back: str = field(repr=False)
    original_source: str = field(repr=False)
    quality: CardQualityResult
    decision: ReviewDecision = ReviewDecision.PENDING
    revision: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be a non-empty string.")
        for value, name in (
            (self.front, "front"),
            (self.back, "back"),
            (self.source, "source"),
            (self.original_front, "original_front"),
            (self.original_back, "original_back"),
            (self.original_source, "original_source"),
        ):
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a string.")
        if not isinstance(self.quality, CardQualityResult):
            raise ValueError("quality must be a CardQualityResult.")
        if not isinstance(self.decision, ReviewDecision):
            raise ValueError("decision must be a ReviewDecision.")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise ValueError("revision must be a non-negative integer.")
        if self.revision < 0:
            raise ValueError("revision must be a non-negative integer.")

    @classmethod
    def create(
        cls,
        candidate_id: str,
        front: str,
        back: str,
        source: str = "",
    ) -> "ReviewCandidate":
        return cls(
            candidate_id=candidate_id,
            front=front,
            back=back,
            source=source,
            original_front=front,
            original_back=back,
            original_source=source,
            quality=evaluate_card_quality(front, back),
        )

    def __repr__(self) -> str:
        return (
            "ReviewCandidate("
            f"candidate_id={self.candidate_id!r}, decision={self.decision.value!r}, "
            f"revision={self.revision}, quality={self.quality!r}, "
            f"front_chars={len(self.front)}, back_chars={len(self.back)}, "
            f"source_chars={len(self.source)})"
        )


@dataclass(frozen=True)
class ReviewStats:
    total_count: int
    pending_count: int
    kept_count: int
    discarded_count: int
    warning_count: int
    blocking_count: int


@dataclass(frozen=True, repr=False)
class ReviewWorkbench:
    cards: tuple[ReviewCandidate, ...]
    duplicate_check_current: bool = False
    write_preview_current: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.cards, tuple) or not all(
            isinstance(item, ReviewCandidate) for item in self.cards
        ):
            raise ValueError("cards must be a tuple of ReviewCandidate values.")
        candidate_ids = tuple(item.candidate_id for item in self.cards)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate ids must be unique.")
        for value, name in (
            (self.duplicate_check_current, "duplicate_check_current"),
            (self.write_preview_current, "write_preview_current"),
        ):
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean.")

    @classmethod
    def from_candidates(
        cls,
        candidates: Iterable[ReviewCandidate],
    ) -> "ReviewWorkbench":
        if isinstance(candidates, (str, bytes)):
            raise ValueError("candidates must contain ReviewCandidate values.")
        return cls(tuple(candidates))

    @property
    def stats(self) -> ReviewStats:
        return ReviewStats(
            total_count=len(self.cards),
            pending_count=sum(
                item.decision is ReviewDecision.PENDING for item in self.cards
            ),
            kept_count=sum(item.decision is ReviewDecision.KEPT for item in self.cards),
            discarded_count=sum(
                item.decision is ReviewDecision.DISCARDED for item in self.cards
            ),
            warning_count=sum(item.quality.severity == "warning" for item in self.cards),
            blocking_count=sum(item.quality.is_blocking for item in self.cards),
        )

    def card(self, candidate_id: str) -> ReviewCandidate:
        for item in self.cards:
            if item.candidate_id == candidate_id:
                return item
        raise KeyError(candidate_id)

    def with_current_write_artifacts(self) -> "ReviewWorkbench":
        return replace(
            self,
            duplicate_check_current=True,
            write_preview_current=True,
        )

    def keep(self, candidate_id: str) -> "ReviewWorkbench":
        card = self.card(candidate_id)
        if card.quality.is_blocking:
            raise ValueError("blocking candidate cannot be kept.")
        return self._replace_card(replace(card, decision=ReviewDecision.KEPT))

    def discard(self, candidate_id: str) -> "ReviewWorkbench":
        card = self.card(candidate_id)
        return self._replace_card(replace(card, decision=ReviewDecision.DISCARDED))

    def edit(self, candidate_id: str, front: str, back: str) -> "ReviewWorkbench":
        if not isinstance(front, str) or not isinstance(back, str):
            raise ValueError("front and back must be strings.")
        card = self.card(candidate_id)
        updated = replace(
            card,
            front=front,
            back=back,
            quality=evaluate_card_quality(front, back),
            decision=ReviewDecision.PENDING,
            revision=card.revision + 1,
        )
        return self._replace_card(updated)

    def restore(self, candidate_id: str) -> "ReviewWorkbench":
        card = self.card(candidate_id)
        updated = replace(
            card,
            front=card.original_front,
            back=card.original_back,
            source=card.original_source,
            quality=evaluate_card_quality(card.original_front, card.original_back),
            decision=ReviewDecision.PENDING,
            revision=card.revision + 1,
        )
        return self._replace_card(updated)

    def copy(self, candidate_id: str, new_candidate_id: str) -> "ReviewWorkbench":
        if any(item.candidate_id == new_candidate_id for item in self.cards):
            raise ValueError("candidate ids must be unique.")
        source = self.card(candidate_id)
        copied = ReviewCandidate.create(
            new_candidate_id,
            source.front,
            source.back,
            source.source,
        )
        return ReviewWorkbench((*self.cards, copied))

    def discard_blocking(self) -> "ReviewWorkbench":
        cards = tuple(
            replace(item, decision=ReviewDecision.DISCARDED)
            if item.quality.is_blocking
            else item
            for item in self.cards
        )
        return self._with_mutated_cards(cards)

    def keep_clean(self) -> "ReviewWorkbench":
        cards = tuple(
            replace(item, decision=ReviewDecision.KEPT)
            if item.decision is ReviewDecision.PENDING
            and item.quality.severity == "info"
            else item
            for item in self.cards
        )
        return self._with_mutated_cards(cards)

    def to_safe_dict(self) -> dict:
        stats = self.stats
        return {
            "total_count": stats.total_count,
            "pending_count": stats.pending_count,
            "kept_count": stats.kept_count,
            "discarded_count": stats.discarded_count,
            "warning_count": stats.warning_count,
            "blocking_count": stats.blocking_count,
            "duplicate_check_current": self.duplicate_check_current,
            "write_preview_current": self.write_preview_current,
        }

    def __repr__(self) -> str:
        stats = self.stats
        return (
            "ReviewWorkbench("
            f"total_count={stats.total_count}, pending_count={stats.pending_count}, "
            f"kept_count={stats.kept_count}, discarded_count={stats.discarded_count}, "
            f"warning_count={stats.warning_count}, blocking_count={stats.blocking_count}, "
            f"duplicate_check_current={self.duplicate_check_current}, "
            f"write_preview_current={self.write_preview_current})"
        )

    def _replace_card(self, updated: ReviewCandidate) -> "ReviewWorkbench":
        cards = tuple(
            updated if item.candidate_id == updated.candidate_id else item
            for item in self.cards
        )
        return ReviewWorkbench(cards)

    def _with_mutated_cards(
        self,
        cards: tuple[ReviewCandidate, ...],
    ) -> "ReviewWorkbench":
        if cards == self.cards:
            return self
        return ReviewWorkbench(cards)
