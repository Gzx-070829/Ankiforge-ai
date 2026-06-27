"""Pure controlled-write eligibility and read-only preview helpers."""

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .card_candidate_preview_adapter import (
    CardCandidatePreviewItem,
    build_card_candidate_preview_item,
    build_card_candidate_preview_items,
)
from .models import CardCandidate, HumanReview, QualityGateResult


@dataclass(frozen=True)
class PipelineWriteEligibility:
    candidate_id: str
    eligible: bool
    quality_status: str
    review_status: str
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class WriteReadyPreviewItem:
    """Immutable preview data; this object does not authorize an Anki write."""

    candidate_id: str
    card_type: str
    front: str
    back: str
    extra: str
    tags: Tuple[str, ...]
    source: str
    source_display: str
    quality_status: str
    review_status: str


def build_pipeline_write_eligibility(
    candidate: CardCandidate,
    quality_result: Optional[QualityGateResult] = None,
    review: Optional[HumanReview] = None,
) -> PipelineWriteEligibility:
    """Describe eligibility by reusing the existing preview policy."""
    preview = build_card_candidate_preview_item(candidate, quality_result, review)
    return _build_eligibility_from_preview(preview)


def build_write_ready_preview_item(
    candidate: CardCandidate,
    quality_result: Optional[QualityGateResult] = None,
    review: Optional[HumanReview] = None,
) -> WriteReadyPreviewItem:
    """Build a read-only item only when quality and review permit it."""
    preview = build_card_candidate_preview_item(candidate, quality_result, review)
    eligibility = _build_eligibility_from_preview(preview)
    if not eligibility.eligible:
        reasons = ", ".join(eligibility.reasons) or "not_write_eligible"
        raise ValueError(
            f"Candidate {candidate.candidate_id} is not write eligible: {reasons}."
        )
    return _build_write_ready_item_from_preview(preview)


def build_write_ready_preview_items(
    candidates: Iterable[CardCandidate],
    quality_results: Optional[Iterable[QualityGateResult]] = None,
    reviews: Optional[Iterable[HumanReview]] = None,
) -> List[WriteReadyPreviewItem]:
    """Filter eligible candidates into immutable previews in input order."""
    previews = build_card_candidate_preview_items(
        candidates,
        quality_results,
        reviews,
    )
    return [
        _build_write_ready_item_from_preview(preview)
        for preview in previews
        if preview.review_allows_write
    ]


def _build_eligibility_from_preview(
    preview: CardCandidatePreviewItem,
) -> PipelineWriteEligibility:
    reasons = []
    if preview.quality_status == "unchecked":
        reasons.append("quality_unchecked")
    elif preview.quality_status == "failed":
        reasons.append("quality_failed")

    if preview.review_status == "unreviewed":
        reasons.append("review_missing")
    elif preview.review_status != "approved":
        reasons.append("review_not_approved")

    return PipelineWriteEligibility(
        candidate_id=preview.candidate_id,
        eligible=preview.review_allows_write,
        quality_status=preview.quality_status,
        review_status=preview.review_status,
        reasons=tuple(reasons),
    )


def _build_write_ready_item_from_preview(
    preview: CardCandidatePreviewItem,
) -> WriteReadyPreviewItem:
    return WriteReadyPreviewItem(
        candidate_id=preview.candidate_id,
        card_type=preview.card_type,
        front=preview.front,
        back=preview.back,
        extra=preview.extra,
        tags=tuple(preview.tags),
        source=preview.source,
        source_display=preview.source_display,
        quality_status=preview.quality_status,
        review_status=preview.review_status,
    )
