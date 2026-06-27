"""Pure read-only adapter for pipeline card candidate previews."""

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .models import CardCandidate, HumanReview, QualityGateResult, QualityIssue


@dataclass(frozen=True)
class QualityIssuePreviewItem:
    code: str
    message: str
    severity: str


@dataclass(frozen=True)
class CardCandidatePreviewItem:
    candidate_id: str
    card_type: str
    front: str
    back: str
    extra: str
    tags: Tuple[str, ...]
    source: str
    source_display: str
    quality_status: str
    quality_issues: Tuple[QualityIssuePreviewItem, ...]
    review_decision: str
    quality_allows_approval: bool


def build_card_candidate_preview_item(
    candidate: CardCandidate,
    quality_result: Optional[QualityGateResult] = None,
    review: Optional[HumanReview] = None,
) -> CardCandidatePreviewItem:
    _validate_candidate_ids(candidate, quality_result, review)

    if quality_result is None:
        quality_status = "unchecked"
        quality_issues: Tuple[QualityIssuePreviewItem, ...] = ()
        quality_allows_approval = False
    else:
        quality_status = "passed" if quality_result.passed else "failed"
        quality_issues = tuple(
            _build_quality_issue_preview(issue) for issue in quality_result.issues
        )
        quality_allows_approval = quality_result.passed

    return CardCandidatePreviewItem(
        candidate_id=candidate.candidate_id,
        card_type=candidate.card_type,
        front=candidate.front,
        back=candidate.back,
        extra=candidate.extra,
        tags=tuple(candidate.tags),
        source=candidate.source,
        source_display=candidate.source_display,
        quality_status=quality_status,
        quality_issues=quality_issues,
        review_decision=review.decision if review is not None else "",
        quality_allows_approval=quality_allows_approval,
    )


def build_card_candidate_preview_items(
    candidates: Iterable[CardCandidate],
    quality_results: Optional[Iterable[QualityGateResult]] = None,
    reviews: Optional[Iterable[HumanReview]] = None,
) -> List[CardCandidatePreviewItem]:
    candidate_list = list(candidates)
    quality_list = _optional_items(
        quality_results,
        len(candidate_list),
        "Candidates and quality results must have the same length.",
    )
    review_list = _optional_items(
        reviews,
        len(candidate_list),
        "Candidates and human reviews must have the same length.",
    )

    return [
        build_card_candidate_preview_item(candidate, quality_result, review)
        for candidate, quality_result, review in zip(
            candidate_list,
            quality_list,
            review_list,
        )
    ]


def _validate_candidate_ids(
    candidate: CardCandidate,
    quality_result: Optional[QualityGateResult],
    review: Optional[HumanReview],
) -> None:
    if (
        quality_result is not None
        and candidate.candidate_id != quality_result.candidate_id
    ):
        raise ValueError("Candidate and quality result candidate IDs must match.")
    if review is not None and candidate.candidate_id != review.candidate_id:
        raise ValueError("Candidate and human review candidate IDs must match.")


def _build_quality_issue_preview(issue: QualityIssue) -> QualityIssuePreviewItem:
    return QualityIssuePreviewItem(
        code=issue.code,
        message=issue.message,
        severity=issue.severity,
    )


def _optional_items(items, expected_length: int, error_message: str):
    if items is None:
        return [None] * expected_length
    item_list = list(items)
    if len(item_list) != expected_length:
        raise ValueError(error_message)
    return item_list
