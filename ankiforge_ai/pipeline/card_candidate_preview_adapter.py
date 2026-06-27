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
class QualityReviewPreviewState:
    quality_status: str
    review_status: str
    has_quality_errors: bool
    has_quality_warnings: bool
    quality_allows_approval: bool
    review_allows_write: bool


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
    has_quality_errors: bool = False
    has_quality_warnings: bool = False
    review_status: str = "unreviewed"
    review_allows_write: bool = False


def build_quality_review_preview_state(
    quality_result: Optional[QualityGateResult] = None,
    review: Optional[HumanReview] = None,
) -> QualityReviewPreviewState:
    """Derive read-only display state without granting write authorization."""
    issues = quality_result.issues if quality_result is not None else ()
    has_quality_errors = any(issue.severity == "error" for issue in issues)
    has_quality_warnings = any(issue.severity == "warning" for issue in issues)

    if quality_result is None:
        quality_status = "unchecked"
        quality_allows_approval = False
    elif has_quality_errors:
        quality_status = "failed"
        quality_allows_approval = False
    elif has_quality_warnings:
        quality_status = "warning"
        quality_allows_approval = True
    else:
        quality_status = "passed"
        quality_allows_approval = True

    review_status = review.decision if review is not None else "unreviewed"
    return QualityReviewPreviewState(
        quality_status=quality_status,
        review_status=review_status,
        has_quality_errors=has_quality_errors,
        has_quality_warnings=has_quality_warnings,
        quality_allows_approval=quality_allows_approval,
        review_allows_write=(
            quality_allows_approval and review_status == "approved"
        ),
    )


def build_card_candidate_preview_item(
    candidate: CardCandidate,
    quality_result: Optional[QualityGateResult] = None,
    review: Optional[HumanReview] = None,
) -> CardCandidatePreviewItem:
    _validate_candidate_ids(candidate, quality_result, review)
    state = build_quality_review_preview_state(quality_result, review)

    if quality_result is None:
        quality_issues: Tuple[QualityIssuePreviewItem, ...] = ()
    else:
        quality_issues = tuple(
            _build_quality_issue_preview(issue) for issue in quality_result.issues
        )

    return CardCandidatePreviewItem(
        candidate_id=candidate.candidate_id,
        card_type=candidate.card_type,
        front=candidate.front,
        back=candidate.back,
        extra=candidate.extra,
        tags=tuple(candidate.tags),
        source=candidate.source,
        source_display=candidate.source_display,
        quality_status=state.quality_status,
        quality_issues=quality_issues,
        review_decision=review.decision if review is not None else "",
        quality_allows_approval=state.quality_allows_approval,
        has_quality_errors=state.has_quality_errors,
        has_quality_warnings=state.has_quality_warnings,
        review_status=state.review_status,
        review_allows_write=state.review_allows_write,
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
