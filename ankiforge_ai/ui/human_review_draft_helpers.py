"""Pure presentation helpers for an in-memory human-review decision draft."""

from dataclasses import dataclass, field

from ..pipeline.card_candidate_preview_adapter import (
    CardCandidatePreviewItem,
    QualityIssuePreviewItem,
)


HUMAN_REVIEW_DRAFT_DECISIONS = (
    "pending",
    "approved",
    "rejected",
    "needs_edit",
)
EMPTY_HUMAN_REVIEW_DRAFT_MESSAGE = "尚无新 pipeline 候选；仅显示安全空状态。"
_SUMMARY_MAX_CHARS = 120


@dataclass(frozen=True)
class HumanReviewDecisionDraftInput:
    """One local decision and note owned by the currently open dialog."""

    candidate_id: str = field(repr=False)
    decision: str = "pending"
    reviewer_note: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be a non-empty string.")
        if self.decision not in HUMAN_REVIEW_DRAFT_DECISIONS:
            raise ValueError("decision is not a supported review draft decision.")
        if not isinstance(self.reviewer_note, str):
            raise ValueError("reviewer_note must be a string.")

    def to_safe_dict(self) -> dict:
        return {
            "candidate_id_present": bool(self.candidate_id.strip()),
            "candidate_id_length": len(self.candidate_id),
            "decision": self.decision,
            "reviewer_note_present": bool(self.reviewer_note.strip()),
            "reviewer_note_length": len(self.reviewer_note),
        }


@dataclass(frozen=True)
class HumanReviewDraftDisplayRow:
    """Whitelisted UI text whose value is excluded from repr."""

    label: str
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("label must be a non-empty string.")
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("value must be a non-empty string.")

    def to_safe_dict(self) -> dict:
        return {
            "label": self.label,
            "has_value": bool(self.value),
            "value_length": len(self.value),
        }


@dataclass(frozen=True)
class HumanReviewDecisionDraftViewData:
    """UI-ready local draft state with no formal-review or write authority."""

    is_empty: bool
    is_valid: bool
    summary_message: str
    decision: str
    approval_allowed: bool
    reviewer_note_present: bool
    reviewer_note_length: int
    candidate_rows: tuple[HumanReviewDraftDisplayRow, ...]
    quality_rows: tuple[HumanReviewDraftDisplayRow, ...]
    safety_rows: tuple[HumanReviewDraftDisplayRow, ...]
    validation_errors: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.is_empty) is not bool or type(self.is_valid) is not bool:
            raise ValueError("is_empty and is_valid must be bool values.")
        if not isinstance(self.summary_message, str) or not self.summary_message:
            raise ValueError("summary_message must be a non-empty string.")
        if self.decision not in HUMAN_REVIEW_DRAFT_DECISIONS:
            raise ValueError("decision is not supported.")
        if type(self.approval_allowed) is not bool:
            raise ValueError("approval_allowed must be a bool.")
        if type(self.reviewer_note_present) is not bool:
            raise ValueError("reviewer_note_present must be a bool.")
        if (
            isinstance(self.reviewer_note_length, bool)
            or not isinstance(self.reviewer_note_length, int)
            or self.reviewer_note_length < 0
        ):
            raise ValueError("reviewer_note_length must be a non-negative int.")
        for rows_name, rows in (
            ("candidate_rows", self.candidate_rows),
            ("quality_rows", self.quality_rows),
            ("safety_rows", self.safety_rows),
        ):
            if not isinstance(rows, tuple) or not all(
                isinstance(row, HumanReviewDraftDisplayRow) for row in rows
            ):
                raise ValueError(f"{rows_name} has an invalid row type.")
        if not isinstance(self.validation_errors, tuple) or not all(
            isinstance(error, str) and error for error in self.validation_errors
        ):
            raise ValueError("validation_errors must contain non-empty strings.")

    def to_safe_dict(self) -> dict:
        return {
            "is_empty": self.is_empty,
            "is_valid": self.is_valid,
            "summary_message": self.summary_message,
            "decision": self.decision,
            "approval_allowed": self.approval_allowed,
            "reviewer_note_present": self.reviewer_note_present,
            "reviewer_note_length": self.reviewer_note_length,
            "candidate_rows": tuple(row.to_safe_dict() for row in self.candidate_rows),
            "quality_rows": tuple(row.to_safe_dict() for row in self.quality_rows),
            "safety_rows": tuple(row.to_safe_dict() for row in self.safety_rows),
            "validation_errors": self.validation_errors,
        }


def build_human_review_decision_draft_view_data(
    candidate: CardCandidatePreviewItem | None,
    draft: HumanReviewDecisionDraftInput | None = None,
) -> HumanReviewDecisionDraftViewData:
    """Validate and present one non-persistent review decision draft."""
    if candidate is None:
        if draft is not None:
            raise ValueError("draft requires a candidate preview.")
        return HumanReviewDecisionDraftViewData(
            is_empty=True,
            is_valid=True,
            summary_message=EMPTY_HUMAN_REVIEW_DRAFT_MESSAGE,
            decision="pending",
            approval_allowed=False,
            reviewer_note_present=False,
            reviewer_note_length=0,
            candidate_rows=(),
            quality_rows=(),
            safety_rows=_fixed_safety_rows(),
            validation_errors=(),
        )
    if not isinstance(candidate, CardCandidatePreviewItem):
        raise ValueError("candidate must be CardCandidatePreviewItem or None.")

    _validate_candidate_preview(candidate)
    if draft is None:
        draft = HumanReviewDecisionDraftInput(candidate_id=candidate.candidate_id)
    if not isinstance(draft, HumanReviewDecisionDraftInput):
        raise ValueError("draft must be HumanReviewDecisionDraftInput or None.")
    if draft.candidate_id != candidate.candidate_id:
        raise ValueError("draft and candidate IDs must match.")

    approval_allowed = _approval_allowed(candidate)
    validation_errors = ()
    if draft.decision == "approved" and not approval_allowed:
        validation_errors = (
            "当前 Quality Gate 状态不允许 approved 审核草稿。",
        )

    return HumanReviewDecisionDraftViewData(
        is_empty=False,
        is_valid=not validation_errors,
        summary_message=(
            "本地审核草稿有效；尚未形成正式 HumanReview。"
            if not validation_errors
            else "本地审核草稿未通过校验。"
        ),
        decision=draft.decision,
        approval_allowed=approval_allowed,
        reviewer_note_present=bool(draft.reviewer_note.strip()),
        reviewer_note_length=len(draft.reviewer_note),
        candidate_rows=_candidate_rows(candidate),
        quality_rows=_quality_rows(candidate, approval_allowed),
        safety_rows=_fixed_safety_rows(),
        validation_errors=validation_errors,
    )


def allowed_human_review_draft_decisions(
    view_data: HumanReviewDecisionDraftViewData,
) -> tuple[str, ...]:
    """Return UI choices without duplicating the approval policy in Qt code."""
    if not isinstance(view_data, HumanReviewDecisionDraftViewData):
        raise ValueError("view_data must be HumanReviewDecisionDraftViewData.")
    if view_data.is_empty or not view_data.approval_allowed:
        return tuple(
            decision
            for decision in HUMAN_REVIEW_DRAFT_DECISIONS
            if decision != "approved"
        )
    return HUMAN_REVIEW_DRAFT_DECISIONS


def _validate_candidate_preview(candidate: CardCandidatePreviewItem) -> None:
    if not isinstance(candidate.candidate_id, str) or not candidate.candidate_id.strip():
        raise ValueError("candidate preview must have a candidate ID.")
    if candidate.quality_status not in {"unchecked", "passed", "warning", "failed"}:
        raise ValueError("candidate preview has an invalid quality status.")
    expected_approval = candidate.quality_status in {"passed", "warning"}
    if candidate.quality_allows_approval is not expected_approval:
        raise ValueError("candidate preview has an inconsistent approval state.")
    if candidate.has_quality_errors is not (candidate.quality_status == "failed"):
        raise ValueError("candidate preview has an inconsistent error state.")
    if not isinstance(candidate.quality_issues, tuple) or not all(
        isinstance(issue, QualityIssuePreviewItem)
        for issue in candidate.quality_issues
    ):
        raise ValueError("candidate preview has invalid quality issues.")


def _approval_allowed(candidate: CardCandidatePreviewItem) -> bool:
    return (
        candidate.quality_status in {"passed", "warning"}
        and candidate.quality_allows_approval is True
        and candidate.has_quality_errors is False
    )


def _candidate_rows(
    candidate: CardCandidatePreviewItem,
) -> tuple[HumanReviewDraftDisplayRow, ...]:
    return (
        _row("Candidate ID", candidate.candidate_id),
        _row("Front preview", _summary(candidate.front)),
        _row("Back preview", _summary(candidate.back)),
        _row("Source preview", _summary(candidate.source_display or candidate.source)),
    )


def _quality_rows(
    candidate: CardCandidatePreviewItem,
    approval_allowed: bool,
) -> tuple[HumanReviewDraftDisplayRow, ...]:
    rows = [
        _row("Quality status", candidate.quality_status),
        _row("Approved draft allowed", "是" if approval_allowed else "否"),
    ]
    if not candidate.quality_issues:
        rows.append(_row("Quality issues", "无"))
    else:
        rows.extend(
            _row(
                f"Issue {issue.code} ({issue.severity})",
                _summary(issue.message),
            )
            for issue in candidate.quality_issues
        )
    return tuple(rows)


def _fixed_safety_rows() -> tuple[HumanReviewDraftDisplayRow, ...]:
    return (
        _row("Draft scope", "仅审核草稿"),
        _row("Formal HumanReview", "尚未形成正式 HumanReview"),
        _row("Write authorization", "尚未计算写入授权"),
        _row("Will generate GeneratedCard", "否"),
        _row("Will modify legacy candidates", "否（不修改 legacy 候选卡）"),
        _row("Will call writer", "否（不调用 writer）"),
        _row("Will write to Anki", "否（不写入 Anki）"),
        _row("Draft lifetime", "仅当前弹窗，关闭后丢弃"),
    )


def _summary(value: str) -> str:
    normalized = " ".join(str(value or "").split())
    if not normalized:
        return "（空）"
    if len(normalized) <= _SUMMARY_MAX_CHARS:
        return normalized
    return normalized[: _SUMMARY_MAX_CHARS - 3].rstrip() + "..."


def _row(label: str, value: str) -> HumanReviewDraftDisplayRow:
    return HumanReviewDraftDisplayRow(label=label, value=value)
