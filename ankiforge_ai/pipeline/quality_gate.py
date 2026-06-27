"""Deterministic structural quality checks for card candidates."""

from typing import Iterable, List

from .models import CardCandidate, QualityGateResult, QualityIssue

FRONT_MAX_LENGTH = 200
BACK_MIN_LENGTH = 8
VALID_SEVERITIES = {"warning", "error"}


def validate_quality_issue(issue: QualityIssue) -> QualityIssue:
    if not isinstance(issue.code, str) or not issue.code.strip():
        raise ValueError("Quality issue code must be a non-empty string.")
    if not isinstance(issue.message, str) or not issue.message.strip():
        raise ValueError("Quality issue message must be a non-empty string.")
    if issue.severity not in VALID_SEVERITIES:
        raise ValueError("Quality issue severity must be warning or error.")
    return issue


def run_quality_gate(candidate: CardCandidate) -> QualityGateResult:
    front = str(candidate.front or "").strip()
    back = str(candidate.back or "").strip()
    source = str(candidate.source or "").strip()
    issues = []

    if candidate.card_type != "basic":
        issues.append(
            QualityIssue(
                code="unsupported_card_type",
                message="Only basic card candidates are supported.",
                severity="error",
            )
        )
    if not front:
        issues.append(
            QualityIssue(
                code="empty_front",
                message="Front must not be empty.",
                severity="error",
            )
        )
    if not back:
        issues.append(
            QualityIssue(
                code="empty_back",
                message="Back must not be empty.",
                severity="error",
            )
        )
    if front == back:
        issues.append(
            QualityIssue(
                code="front_back_same",
                message="Front and back should not be identical.",
                severity="warning",
            )
        )
    if len(front) > FRONT_MAX_LENGTH:
        issues.append(
            QualityIssue(
                code="front_too_long",
                message="Front is longer than 200 characters.",
                severity="warning",
            )
        )
    if len(back) < BACK_MIN_LENGTH:
        issues.append(
            QualityIssue(
                code="back_too_short",
                message="Back is shorter than 8 characters.",
                severity="warning",
            )
        )
    if not source:
        issues.append(
            QualityIssue(
                code="missing_source",
                message="Source is missing.",
                severity="warning",
            )
        )

    for issue in issues:
        validate_quality_issue(issue)
    return QualityGateResult(candidate_id=candidate.candidate_id, issues=issues)


def run_quality_gate_for_candidates(
    candidates: Iterable[CardCandidate],
) -> List[QualityGateResult]:
    return [run_quality_gate(candidate) for candidate in candidates]
