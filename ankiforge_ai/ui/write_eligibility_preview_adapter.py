"""Build a read-only eligibility summary from a local HumanReview preview."""

from dataclasses import dataclass, field

from .human_review_draft_helpers import HumanReviewDraftDisplayRow
from .human_review_preview_adapter import LocalHumanReviewPreview


WRITE_ELIGIBILITY_STATUSES = (
    "eligible",
    "blocked",
    "needs_review",
    "unknown",
)


@dataclass(frozen=True)
class WriteEligibilityPreview:
    """Descriptive eligibility only; this object grants no write authority."""

    is_empty: bool
    summary_message: str
    candidate_id: str = field(repr=False)
    review_decision: str
    quality_status: str
    review_valid: bool
    eligibility_status: str
    blocking_reasons: tuple[str, ...]
    safety_rows: tuple[HumanReviewDraftDisplayRow, ...]

    def __post_init__(self) -> None:
        if type(self.is_empty) is not bool:
            raise ValueError("is_empty must be a bool.")
        if not isinstance(self.summary_message, str) or not self.summary_message:
            raise ValueError("summary_message must be a non-empty string.")
        if not isinstance(self.candidate_id, str):
            raise ValueError("candidate_id must be a string.")
        if not self.is_empty and not self.candidate_id.strip():
            raise ValueError("non-empty preview requires a candidate ID.")
        if not isinstance(self.review_decision, str):
            raise ValueError("review_decision must be a string.")
        if not isinstance(self.quality_status, str):
            raise ValueError("quality_status must be a string.")
        if type(self.review_valid) is not bool:
            raise ValueError("review_valid must be a bool.")
        if self.eligibility_status not in WRITE_ELIGIBILITY_STATUSES:
            raise ValueError("eligibility_status is not supported.")
        if not isinstance(self.blocking_reasons, tuple) or not all(
            isinstance(reason, str) and reason for reason in self.blocking_reasons
        ):
            raise ValueError("blocking_reasons must contain non-empty strings.")
        if not isinstance(self.safety_rows, tuple) or not all(
            isinstance(row, HumanReviewDraftDisplayRow) for row in self.safety_rows
        ):
            raise ValueError("safety_rows has an invalid row type.")

    def to_safe_dict(self) -> dict:
        return {
            "is_empty": self.is_empty,
            "summary_message": self.summary_message,
            "candidate_id_present": bool(self.candidate_id.strip()),
            "candidate_id_length": len(self.candidate_id),
            "review_decision": self.review_decision,
            "quality_status": self.quality_status,
            "review_valid": self.review_valid,
            "eligibility_status": self.eligibility_status,
            "blocking_reasons": self.blocking_reasons,
            "safety_rows": tuple(row.to_safe_dict() for row in self.safety_rows),
        }


def build_write_eligibility_preview(
    review_preview: LocalHumanReviewPreview | None,
) -> WriteEligibilityPreview:
    """Describe local eligibility without invoking the controlled-write bridge."""
    if review_preview is None:
        return WriteEligibilityPreview(
            is_empty=True,
            summary_message="尚无本地 HumanReview 预览；写入资格状态未知。",
            candidate_id="",
            review_decision="",
            quality_status="",
            review_valid=False,
            eligibility_status="unknown",
            blocking_reasons=("review_preview_missing",),
            safety_rows=_fixed_safety_rows(),
        )
    if not isinstance(review_preview, LocalHumanReviewPreview):
        raise ValueError("review_preview must be LocalHumanReviewPreview or None.")

    _validate_local_review_preview(review_preview)
    eligibility_status, blocking_reasons = _derive_eligibility(review_preview)
    return WriteEligibilityPreview(
        is_empty=False,
        summary_message=_summary_message(eligibility_status),
        candidate_id=review_preview.candidate_id,
        review_decision=review_preview.review_decision,
        quality_status=review_preview.quality_status,
        review_valid=review_preview.is_locally_valid,
        eligibility_status=eligibility_status,
        blocking_reasons=blocking_reasons,
        safety_rows=_fixed_safety_rows(),
    )


def _validate_local_review_preview(preview: LocalHumanReviewPreview) -> None:
    if preview.review_decision not in {
        "pending",
        "approved",
        "rejected",
        "needs_edit",
    }:
        raise ValueError("review preview has an unsupported decision.")
    if preview.quality_status not in {"unchecked", "passed", "warning", "failed"}:
        raise ValueError("review preview has an unsupported quality status.")
    if preview.is_locally_valid == bool(preview.validation_errors):
        raise ValueError("review preview has an inconsistent validation state.")

    expected_safety = (
        ("Created source", "本地审核草稿"),
        ("Preview meaning", "这是本地 HumanReview 预览"),
        ("Persistence", "尚未保存"),
        ("Write authorization", "尚未形成写入授权"),
        ("GeneratedCard", "尚未生成 GeneratedCard"),
        ("WriteReadyPreviewItem", "尚未生成 WriteReadyPreviewItem"),
        ("Writer", "不调用 writer"),
        ("Anki write", "不写入 Anki"),
        ("Lifetime", "仅当前弹窗，关闭后丢弃"),
    )
    if tuple((row.label, row.value) for row in preview.safety_rows) != (
        expected_safety
    ):
        raise ValueError("review preview must retain the PR2 safety boundary.")

    approved_quality = preview.quality_status in {"passed", "warning"}
    if preview.review_decision == "approved":
        if preview.is_locally_valid is not approved_quality:
            raise ValueError("approved preview has an inconsistent quality state.")
    elif not preview.is_locally_valid:
        raise ValueError("non-approved review preview must be locally valid.")


def _derive_eligibility(
    preview: LocalHumanReviewPreview,
) -> tuple[str, tuple[str, ...]]:
    reasons = []
    if preview.quality_status == "failed":
        reasons.append("quality_failed")
    elif preview.quality_status == "unchecked":
        reasons.append("quality_unchecked")

    if preview.review_decision == "approved":
        if not preview.is_locally_valid:
            reasons.append("local_review_invalid")
            return "blocked", tuple(reasons)
        return "eligible", ()
    if preview.review_decision == "pending":
        reasons.append("review_pending")
        return "needs_review", tuple(reasons)
    if preview.review_decision == "rejected":
        reasons.append("review_rejected")
        return "blocked", tuple(reasons)

    reasons.append("review_needs_edit")
    return "blocked", tuple(reasons)


def _summary_message(status: str) -> str:
    if status == "eligible":
        return "满足本地写入资格条件；这不是写入授权。"
    if status == "needs_review":
        return "仍需人工审核；这不是写入授权。"
    return "本地写入资格被阻止；这不是写入授权。"


def _fixed_safety_rows() -> tuple[HumanReviewDraftDisplayRow, ...]:
    return (
        _row("Generated source", "本地 HumanReview 预览"),
        _row("Summary meaning", "这是只读写入资格摘要"),
        _row("Write authorization", "未授予"),
        _row("Write Plan", "尚未生成 Write Plan"),
        _row("GeneratedCard", "尚未生成 GeneratedCard"),
        _row("WriteReadyPreviewItem", "尚未生成 WriteReadyPreviewItem"),
        _row("Writer", "不调用 writer"),
        _row("Anki write", "不写入 Anki"),
        _row("Lifetime", "仅当前弹窗，关闭后丢弃"),
    )


def _row(label: str, value: str) -> HumanReviewDraftDisplayRow:
    return HumanReviewDraftDisplayRow(label=label, value=value)
