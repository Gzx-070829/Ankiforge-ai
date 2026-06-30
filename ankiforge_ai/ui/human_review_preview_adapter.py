"""Adapt a PR1 decision draft into a disposable local HumanReview preview."""

from dataclasses import dataclass, field

from .human_review_draft_helpers import (
    HumanReviewDecisionDraftInput,
    HumanReviewDecisionDraftViewData,
    HumanReviewDraftDisplayRow,
)


_NOTE_EXCERPT_MAX_CHARS = 80


@dataclass(frozen=True)
class LocalHumanReviewPreview:
    """Local display object with no persistence or write authority."""

    candidate_id: str = field(repr=False)
    review_decision: str
    reviewer_note_excerpt: str = field(repr=False)
    reviewer_note_length: int
    quality_status: str
    is_locally_valid: bool
    validation_errors: tuple[str, ...]
    safety_rows: tuple[HumanReviewDraftDisplayRow, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be a non-empty string.")
        if not isinstance(self.review_decision, str) or not self.review_decision:
            raise ValueError("review_decision must be a non-empty string.")
        if not isinstance(self.reviewer_note_excerpt, str):
            raise ValueError("reviewer_note_excerpt must be a string.")
        if (
            isinstance(self.reviewer_note_length, bool)
            or not isinstance(self.reviewer_note_length, int)
            or self.reviewer_note_length < 0
        ):
            raise ValueError("reviewer_note_length must be a non-negative int.")
        if not isinstance(self.quality_status, str) or not self.quality_status:
            raise ValueError("quality_status must be a non-empty string.")
        if type(self.is_locally_valid) is not bool:
            raise ValueError("is_locally_valid must be a bool.")
        if not isinstance(self.validation_errors, tuple) or not all(
            isinstance(error, str) and error for error in self.validation_errors
        ):
            raise ValueError("validation_errors must contain non-empty strings.")
        if not isinstance(self.safety_rows, tuple) or not all(
            isinstance(row, HumanReviewDraftDisplayRow) for row in self.safety_rows
        ):
            raise ValueError("safety_rows has an invalid row type.")

    def to_safe_dict(self) -> dict:
        return {
            "candidate_id_present": bool(self.candidate_id.strip()),
            "candidate_id_length": len(self.candidate_id),
            "review_decision": self.review_decision,
            "reviewer_note_present": bool(self.reviewer_note_excerpt),
            "reviewer_note_length": self.reviewer_note_length,
            "quality_status": self.quality_status,
            "is_locally_valid": self.is_locally_valid,
            "validation_errors": self.validation_errors,
            "safety_rows": tuple(row.to_safe_dict() for row in self.safety_rows),
        }


def build_local_human_review_preview(
    view_data: HumanReviewDecisionDraftViewData,
    draft: HumanReviewDecisionDraftInput,
) -> LocalHumanReviewPreview | None:
    """Build a local-only preview from already-validated PR1 presentation data."""
    if not isinstance(view_data, HumanReviewDecisionDraftViewData):
        raise ValueError("view_data must be HumanReviewDecisionDraftViewData.")
    if not isinstance(draft, HumanReviewDecisionDraftInput):
        raise ValueError("draft must be HumanReviewDecisionDraftInput.")
    if view_data.is_empty:
        return None

    candidate_id = _row_value(view_data.candidate_rows, "Candidate ID")
    quality_status = _row_value(view_data.quality_rows, "Quality status")
    _validate_pr1_state(view_data, draft, candidate_id, quality_status)

    return LocalHumanReviewPreview(
        candidate_id=candidate_id,
        review_decision=draft.decision,
        reviewer_note_excerpt=_note_excerpt(draft.reviewer_note),
        reviewer_note_length=len(draft.reviewer_note),
        quality_status=quality_status,
        is_locally_valid=view_data.is_valid,
        validation_errors=view_data.validation_errors,
        safety_rows=_fixed_preview_safety_rows(),
    )


def _validate_pr1_state(
    view_data: HumanReviewDecisionDraftViewData,
    draft: HumanReviewDecisionDraftInput,
    candidate_id: str,
    quality_status: str,
) -> None:
    if draft.candidate_id != candidate_id:
        raise ValueError("draft and view candidate IDs must match.")
    if draft.decision != view_data.decision:
        raise ValueError("draft and view decisions must match.")
    if view_data.reviewer_note_length != len(draft.reviewer_note):
        raise ValueError("draft and view reviewer-note lengths must match.")
    if view_data.reviewer_note_present != bool(draft.reviewer_note.strip()):
        raise ValueError("draft and view reviewer-note presence must match.")
    if quality_status not in {"unchecked", "passed", "warning", "failed"}:
        raise ValueError("view_data has an invalid quality status.")

    expected_safety = (
        ("Draft scope", "仅审核草稿"),
        ("Formal HumanReview", "尚未形成正式 HumanReview"),
        ("Write authorization", "尚未计算写入授权"),
        ("Will generate GeneratedCard", "否"),
        ("Will modify legacy candidates", "否（不修改 legacy 候选卡）"),
        ("Will call writer", "否（不调用 writer）"),
        ("Will write to Anki", "否（不写入 Anki）"),
        ("Draft lifetime", "仅当前弹窗，关闭后丢弃"),
    )
    if tuple((row.label, row.value) for row in view_data.safety_rows) != (
        expected_safety
    ):
        raise ValueError("view_data must retain the PR1 safety boundary.")

    approved_is_allowed = quality_status in {"passed", "warning"}
    if view_data.approval_allowed is not approved_is_allowed:
        raise ValueError("view_data has an inconsistent approval state.")
    if draft.decision == "approved" and not approved_is_allowed:
        if view_data.is_valid or not view_data.validation_errors:
            raise ValueError("invalid approved draft must retain a local error.")
    elif not view_data.is_valid or view_data.validation_errors:
        raise ValueError("non-approved or quality-allowed draft must be locally valid.")


def _fixed_preview_safety_rows() -> tuple[HumanReviewDraftDisplayRow, ...]:
    return (
        _row("Created source", "本地审核草稿"),
        _row("Preview meaning", "这是本地 HumanReview 预览"),
        _row("Persistence", "尚未保存"),
        _row("Write authorization", "尚未形成写入授权"),
        _row("GeneratedCard", "尚未生成 GeneratedCard"),
        _row("WriteReadyPreviewItem", "尚未生成 WriteReadyPreviewItem"),
        _row("Writer", "不调用 writer"),
        _row("Anki write", "不写入 Anki"),
        _row("Lifetime", "仅当前弹窗，关闭后丢弃"),
    )


def _note_excerpt(note: str) -> str:
    normalized = " ".join(note.split())
    if len(normalized) <= _NOTE_EXCERPT_MAX_CHARS:
        return normalized
    return normalized[: _NOTE_EXCERPT_MAX_CHARS - 3].rstrip() + "..."


def _row_value(
    rows: tuple[HumanReviewDraftDisplayRow, ...],
    label: str,
) -> str:
    matches = tuple(row.value for row in rows if row.label == label)
    if len(matches) != 1:
        raise ValueError(f"view_data must contain exactly one {label} row.")
    return matches[0]


def _row(label: str, value: str) -> HumanReviewDraftDisplayRow:
    return HumanReviewDraftDisplayRow(label=label, value=value)
