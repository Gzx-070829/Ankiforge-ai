"""Helpers for creating final human review records in the pipeline."""

from typing import Iterable, List

from .models import CardCandidate, HumanReview, QualityGateResult, QualityIssue

VALID_REVIEW_DECISIONS = {"pending", "approved", "rejected", "needs_edit"}


def build_review_id(candidate_id: str) -> str:
    return f"hr_{candidate_id}"


def create_human_review(
    candidate: CardCandidate,
    quality_result: QualityGateResult,
    decision: str = "pending",
    reviewer_note: str = "",
) -> HumanReview:
    if candidate.candidate_id != quality_result.candidate_id:
        raise ValueError("Candidate and quality result candidate IDs must match.")
    if decision not in VALID_REVIEW_DECISIONS:
        raise ValueError(
            "Invalid human review decision. "
            "Expected pending, approved, rejected, or needs_edit."
        )
    if decision == "approved" and not quality_result.passed:
        raise ValueError("A candidate with quality errors cannot be approved.")

    return HumanReview(
        review_id=build_review_id(candidate.candidate_id),
        candidate_id=candidate.candidate_id,
        selection_id=candidate.selection_id,
        point_id=candidate.point_id,
        document_id=candidate.document_id,
        chunk_id=candidate.chunk_id,
        source_display=candidate.source_display,
        heading_path=list(candidate.heading_path),
        ordinal=candidate.ordinal,
        card_type=candidate.card_type,
        front=candidate.front,
        back=candidate.back,
        extra=candidate.extra,
        tags=list(candidate.tags),
        source=candidate.source,
        quality_passed=quality_result.passed,
        quality_issues=[_copy_quality_issue(issue) for issue in quality_result.issues],
        decision=decision,
        reviewer_note=reviewer_note,
    )


def create_human_reviews(
    candidates: Iterable[CardCandidate],
    quality_results: Iterable[QualityGateResult],
) -> List[HumanReview]:
    candidate_list = list(candidates)
    result_list = list(quality_results)
    if len(candidate_list) != len(result_list):
        raise ValueError("Candidates and quality results must have the same length.")

    return [
        create_human_review(candidate, quality_result)
        for candidate, quality_result in zip(candidate_list, result_list)
    ]


def _copy_quality_issue(issue: QualityIssue) -> QualityIssue:
    return QualityIssue(
        code=issue.code,
        message=issue.message,
        severity=issue.severity,
    )
