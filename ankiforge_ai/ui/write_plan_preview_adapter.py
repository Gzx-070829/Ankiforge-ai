"""Build a non-executing Write Plan preview from eligibility presentation."""

from dataclasses import dataclass, field

from .human_review_draft_helpers import HumanReviewDraftDisplayRow
from .write_eligibility_preview_adapter import WriteEligibilityPreview


WRITE_PLAN_PREVIEW_STATUSES = (
    "ready_preview",
    "blocked",
    "needs_review",
    "unknown",
)


@dataclass(frozen=True)
class WritePlanFieldMapping:
    """One fixed display-only source-to-target field mapping."""

    source_field: str
    target_field: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_field, str) or not self.source_field:
            raise ValueError("source_field must be a non-empty string.")
        if not isinstance(self.target_field, str) or not self.target_field:
            raise ValueError("target_field must be a non-empty string.")

    def to_safe_dict(self) -> dict:
        return {
            "source_field": self.source_field,
            "target_field": self.target_field,
        }


@dataclass(frozen=True)
class ReadOnlyWritePlanPreview:
    """Field-mapping preview with no persistence or execution authority."""

    is_empty: bool
    summary_message: str
    candidate_id: str = field(repr=False)
    eligibility_status: str
    review_decision: str
    quality_status: str
    plan_status: str
    blocking_reasons: tuple[str, ...]
    target_note_type_preview: str
    target_deck_preview: str
    field_mappings: tuple[WritePlanFieldMapping, ...]
    tag_preview: tuple[str, ...]
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
        for field_name in (
            "eligibility_status",
            "review_decision",
            "quality_status",
            "target_note_type_preview",
            "target_deck_preview",
        ):
            if not isinstance(getattr(self, field_name), str):
                raise ValueError(f"{field_name} must be a string.")
        if self.plan_status not in WRITE_PLAN_PREVIEW_STATUSES:
            raise ValueError("plan_status is not supported.")
        if not isinstance(self.blocking_reasons, tuple) or not all(
            isinstance(reason, str) and reason for reason in self.blocking_reasons
        ):
            raise ValueError("blocking_reasons must contain non-empty strings.")
        if not isinstance(self.field_mappings, tuple) or not all(
            isinstance(mapping, WritePlanFieldMapping)
            for mapping in self.field_mappings
        ):
            raise ValueError("field_mappings has an invalid mapping type.")
        if not isinstance(self.tag_preview, tuple) or not all(
            isinstance(tag, str) and tag for tag in self.tag_preview
        ):
            raise ValueError("tag_preview must contain non-empty strings.")
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
            "eligibility_status": self.eligibility_status,
            "review_decision": self.review_decision,
            "quality_status": self.quality_status,
            "plan_status": self.plan_status,
            "blocking_reasons": self.blocking_reasons,
            "target_note_type_preview": self.target_note_type_preview,
            "target_deck_preview": self.target_deck_preview,
            "field_mappings": tuple(
                mapping.to_safe_dict() for mapping in self.field_mappings
            ),
            "tag_preview": self.tag_preview,
            "safety_rows": tuple(row.to_safe_dict() for row in self.safety_rows),
        }


def build_read_only_write_plan_preview(
    eligibility: WriteEligibilityPreview | None,
) -> ReadOnlyWritePlanPreview:
    """Build fixed field mappings without preparing or executing a write."""
    if eligibility is None:
        return _empty_preview("尚无 Write Eligibility 摘要；Write Plan 状态未知。")
    if not isinstance(eligibility, WriteEligibilityPreview):
        raise ValueError("eligibility must be WriteEligibilityPreview or None.")

    _validate_eligibility(eligibility)
    if eligibility.is_empty:
        return _empty_preview("Write Eligibility 状态未知；Write Plan 未生成。")

    plan_status = {
        "eligible": "ready_preview",
        "blocked": "blocked",
        "needs_review": "needs_review",
        "unknown": "unknown",
    }[eligibility.eligibility_status]
    return ReadOnlyWritePlanPreview(
        is_empty=False,
        summary_message=_summary_message(plan_status),
        candidate_id=eligibility.candidate_id,
        eligibility_status=eligibility.eligibility_status,
        review_decision=eligibility.review_decision,
        quality_status=eligibility.quality_status,
        plan_status=plan_status,
        blocking_reasons=eligibility.blocking_reasons,
        target_note_type_preview="未绑定真实 Anki note type，仅预览",
        target_deck_preview="未绑定真实 Anki deck，仅预览",
        field_mappings=_fixed_field_mappings(),
        tag_preview=("AnkiForgeAI", "pipeline-preview", "human-reviewed"),
        safety_rows=_fixed_safety_rows(),
    )


def _validate_eligibility(eligibility: WriteEligibilityPreview) -> None:
    expected_safety = (
        ("Generated source", "本地 HumanReview 预览"),
        ("Summary meaning", "这是只读写入资格摘要"),
        ("Write authorization", "未授予"),
        ("Write Plan", "尚未生成 Write Plan"),
        ("GeneratedCard", "尚未生成 GeneratedCard"),
        ("WriteReadyPreviewItem", "尚未生成 WriteReadyPreviewItem"),
        ("Writer", "不调用 writer"),
        ("Anki write", "不写入 Anki"),
        ("Lifetime", "仅当前弹窗，关闭后丢弃"),
    )
    if tuple((row.label, row.value) for row in eligibility.safety_rows) != (
        expected_safety
    ):
        raise ValueError("eligibility must retain the PR3 safety boundary.")

    if eligibility.is_empty:
        if (
            eligibility.eligibility_status != "unknown"
            or eligibility.candidate_id
            or not eligibility.blocking_reasons
        ):
            raise ValueError("empty eligibility has an inconsistent state.")
        return
    if eligibility.eligibility_status == "eligible":
        if not (
            eligibility.review_valid
            and eligibility.review_decision == "approved"
            and eligibility.quality_status in {"passed", "warning"}
            and not eligibility.blocking_reasons
        ):
            raise ValueError("eligible state is inconsistent.")
        return
    if eligibility.eligibility_status == "needs_review":
        if eligibility.review_decision != "pending" or not eligibility.blocking_reasons:
            raise ValueError("needs-review state is inconsistent.")
        return
    if eligibility.eligibility_status == "blocked":
        if not eligibility.blocking_reasons:
            raise ValueError("blocked state requires reasons.")
        return
    raise ValueError("non-empty eligibility cannot be unknown.")


def _empty_preview(message: str) -> ReadOnlyWritePlanPreview:
    return ReadOnlyWritePlanPreview(
        is_empty=True,
        summary_message=message,
        candidate_id="",
        eligibility_status="unknown",
        review_decision="",
        quality_status="",
        plan_status="unknown",
        blocking_reasons=("eligibility_preview_missing",),
        target_note_type_preview="未绑定真实 Anki note type，仅预览",
        target_deck_preview="未绑定真实 Anki deck，仅预览",
        field_mappings=_fixed_field_mappings(),
        tag_preview=("AnkiForgeAI", "pipeline-preview", "human-reviewed"),
        safety_rows=_fixed_safety_rows(),
    )


def _summary_message(status: str) -> str:
    if status == "ready_preview":
        return "只读 Write Plan 预览已就绪；这不是写入授权。"
    if status == "needs_review":
        return "仍需人工审核；只读 Write Plan 不会执行。"
    if status == "blocked":
        return "Write Plan 预览被阻止；不会执行写入。"
    return "Write Plan 状态未知；不会执行写入。"


def _fixed_field_mappings() -> tuple[WritePlanFieldMapping, ...]:
    return (
        WritePlanFieldMapping("Front", "Front"),
        WritePlanFieldMapping("Back", "Back"),
        WritePlanFieldMapping("Source", "Source"),
    )


def _fixed_safety_rows() -> tuple[HumanReviewDraftDisplayRow, ...]:
    return (
        _row("Source", "本地 Write Eligibility 只读摘要"),
        _row("Preview meaning", "这是只读 Write Plan 预览"),
        _row("Duplicate check", "未执行"),
        _row("Anki collection", "尚未绑定真实 Anki collection"),
        _row("Write authorization", "未授予"),
        _row("Write execution", "不会执行"),
        _row("Persistence", "未保存"),
        _row("GeneratedCard", "尚未生成 GeneratedCard"),
        _row("WriteReadyPreviewItem", "尚未生成 WriteReadyPreviewItem"),
        _row("Writer", "不调用 writer"),
        _row("Anki write", "不写入 Anki"),
        _row("Lifetime", "仅当前弹窗，关闭后丢弃"),
    )


def _row(label: str, value: str) -> HumanReviewDraftDisplayRow:
    return HumanReviewDraftDisplayRow(label=label, value=value)
