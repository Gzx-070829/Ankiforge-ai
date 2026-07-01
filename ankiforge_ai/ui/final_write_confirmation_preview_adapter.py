"""Build a non-executing final write confirmation contract preview."""

from dataclasses import dataclass, field

from .human_review_draft_helpers import HumanReviewDraftDisplayRow
from .write_plan_preview_adapter import ReadOnlyWritePlanPreview


FINAL_CONFIRMATION_PREVIEW_STATUSES = (
    "ready_for_future_confirmation",
    "blocked",
    "needs_review",
    "unknown",
)


@dataclass(frozen=True)
class FinalWriteConfirmationPreview:
    """Read-only contract state that grants no confirmation or write authority."""

    is_empty: bool
    summary_message: str
    candidate_id: str = field(repr=False)
    write_plan_status: str
    eligibility_status: str
    review_decision: str
    final_status: str
    duplicate_check_status: str
    duplicate_check_requirement: str
    duplicate_result: str
    final_confirmation_status: str
    write_authorization: str
    write_execution: str
    required_future_steps: tuple[str, ...]
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
        for field_name in (
            "write_plan_status",
            "eligibility_status",
            "review_decision",
            "duplicate_check_status",
            "duplicate_check_requirement",
            "duplicate_result",
            "final_confirmation_status",
            "write_authorization",
            "write_execution",
        ):
            if not isinstance(getattr(self, field_name), str):
                raise ValueError(f"{field_name} must be a string.")
        if self.final_status not in FINAL_CONFIRMATION_PREVIEW_STATUSES:
            raise ValueError("final_status is not supported.")
        if not isinstance(self.required_future_steps, tuple) or not all(
            isinstance(step, str) and step for step in self.required_future_steps
        ):
            raise ValueError("required_future_steps must contain non-empty strings.")
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
            "write_plan_status": self.write_plan_status,
            "eligibility_status": self.eligibility_status,
            "review_decision": self.review_decision,
            "final_status": self.final_status,
            "duplicate_check_status": self.duplicate_check_status,
            "duplicate_check_requirement": self.duplicate_check_requirement,
            "duplicate_result": self.duplicate_result,
            "final_confirmation_status": self.final_confirmation_status,
            "write_authorization": self.write_authorization,
            "write_execution": self.write_execution,
            "required_future_steps": self.required_future_steps,
            "blocking_reasons": self.blocking_reasons,
            "safety_rows": tuple(row.to_safe_dict() for row in self.safety_rows),
        }


def build_final_write_confirmation_preview(
    write_plan: ReadOnlyWritePlanPreview | None,
) -> FinalWriteConfirmationPreview:
    """Describe future gates without checking duplicates or requesting consent."""
    if write_plan is None:
        return _empty_preview("尚无只读 Write Plan 预览；最终确认契约状态未知。")
    if not isinstance(write_plan, ReadOnlyWritePlanPreview):
        raise ValueError("write_plan must be ReadOnlyWritePlanPreview or None.")

    _validate_write_plan(write_plan)
    if write_plan.is_empty:
        return _empty_preview("Write Plan 状态未知；最终确认尚未请求。")

    final_status = {
        "ready_preview": "ready_for_future_confirmation",
        "blocked": "blocked",
        "needs_review": "needs_review",
        "unknown": "unknown",
    }[write_plan.plan_status]
    return FinalWriteConfirmationPreview(
        is_empty=False,
        summary_message=_summary_message(final_status),
        candidate_id=write_plan.candidate_id,
        write_plan_status=write_plan.plan_status,
        eligibility_status=write_plan.eligibility_status,
        review_decision=write_plan.review_decision,
        final_status=final_status,
        duplicate_check_status="not_run",
        duplicate_check_requirement="required_before_write",
        duplicate_result="unknown",
        final_confirmation_status="not_requested",
        write_authorization="not_granted",
        write_execution="will_not_execute",
        required_future_steps=_required_future_steps(),
        blocking_reasons=write_plan.blocking_reasons,
        safety_rows=_fixed_safety_rows(),
    )


def _validate_write_plan(write_plan: ReadOnlyWritePlanPreview) -> None:
    expected_safety = (
        ("Source", "本地 Write Eligibility 只读摘要"),
        ("Preview meaning", "这是只读 Write Plan 预览"),
        ("Duplicate check", "未执行"),
        ("Anki collection", "尚未绑定真实 Anki collection"),
        ("Write authorization", "未授予"),
        ("Write execution", "不会执行"),
        ("Persistence", "未保存"),
        ("GeneratedCard", "尚未生成 GeneratedCard"),
        ("WriteReadyPreviewItem", "尚未生成 WriteReadyPreviewItem"),
        ("Writer", "不调用 writer"),
        ("Anki write", "不写入 Anki"),
        ("Lifetime", "仅当前弹窗，关闭后丢弃"),
    )
    if tuple((row.label, row.value) for row in write_plan.safety_rows) != (
        expected_safety
    ):
        raise ValueError("write plan must retain the PR4 safety boundary.")
    if write_plan.target_note_type_preview != "未绑定真实 Anki note type，仅预览":
        raise ValueError("write plan must not bind a real note type.")
    if write_plan.target_deck_preview != "未绑定真实 Anki deck，仅预览":
        raise ValueError("write plan must not bind a real deck.")
    if tuple(
        (mapping.source_field, mapping.target_field)
        for mapping in write_plan.field_mappings
    ) != (("Front", "Front"), ("Back", "Back"), ("Source", "Source")):
        raise ValueError("write plan field mappings are not the fixed preview rules.")
    if write_plan.tag_preview != (
        "AnkiForgeAI",
        "pipeline-preview",
        "human-reviewed",
    ):
        raise ValueError("write plan tags are not the fixed preview tags.")

    if write_plan.is_empty:
        if not (
            write_plan.plan_status == "unknown"
            and write_plan.eligibility_status == "unknown"
            and not write_plan.candidate_id
            and write_plan.blocking_reasons == ("eligibility_preview_missing",)
        ):
            raise ValueError("empty write plan has an inconsistent state.")
        return

    allowed_reasons = {
        "quality_failed",
        "quality_unchecked",
        "local_review_invalid",
        "review_pending",
        "review_rejected",
        "review_needs_edit",
    }
    if not set(write_plan.blocking_reasons).issubset(allowed_reasons):
        raise ValueError("write plan contains an unsupported blocking reason.")
    if write_plan.plan_status == "ready_preview":
        if not (
            write_plan.eligibility_status == "eligible"
            and write_plan.review_decision == "approved"
            and write_plan.quality_status in {"passed", "warning"}
            and not write_plan.blocking_reasons
        ):
            raise ValueError("ready write plan has an inconsistent state.")
        return
    if write_plan.plan_status == "needs_review":
        if not (
            write_plan.eligibility_status == "needs_review"
            and write_plan.review_decision == "pending"
            and "review_pending" in write_plan.blocking_reasons
        ):
            raise ValueError("needs-review write plan has an inconsistent state.")
        return
    if write_plan.plan_status == "blocked":
        if not (
            write_plan.eligibility_status == "blocked"
            and write_plan.review_decision in {"approved", "rejected", "needs_edit"}
            and write_plan.blocking_reasons
        ):
            raise ValueError("blocked write plan has an inconsistent state.")
        return
    raise ValueError("non-empty write plan cannot have unknown status.")


def _empty_preview(message: str) -> FinalWriteConfirmationPreview:
    return FinalWriteConfirmationPreview(
        is_empty=True,
        summary_message=message,
        candidate_id="",
        write_plan_status="unknown",
        eligibility_status="unknown",
        review_decision="",
        final_status="unknown",
        duplicate_check_status="not_run",
        duplicate_check_requirement="required_before_write",
        duplicate_result="unknown",
        final_confirmation_status="not_requested",
        write_authorization="not_granted",
        write_execution="will_not_execute",
        required_future_steps=_required_future_steps(),
        blocking_reasons=("write_plan_preview_missing",),
        safety_rows=_fixed_safety_rows(),
    )


def _summary_message(status: str) -> str:
    if status == "ready_for_future_confirmation":
        return "可进入未来确认流程；这不是用户确认，也不是写入授权。"
    if status == "needs_review":
        return "仍需人工审核；最终确认尚未请求。"
    if status == "blocked":
        return "最终确认契约被阻止；不会执行写入。"
    return "最终确认契约状态未知；不会执行写入。"


def _required_future_steps() -> tuple[str, ...]:
    return (
        "重新展示并确认候选内容",
        "绑定真实 Anki note type 与 deck",
        "在独立授权流程中执行 duplicate check",
        "展示 duplicate check 结果",
        "请求独立的最终用户确认",
        "仅在确认后重新计算写入授权",
    )


def _fixed_safety_rows() -> tuple[HumanReviewDraftDisplayRow, ...]:
    return (
        _row("Source", "只读 Write Plan 预览"),
        _row("Preview meaning", "这是最终确认契约预览"),
        _row("User confirmation", "这不是用户确认"),
        _row("Duplicate check", "尚未执行"),
        _row("Anki collection", "尚未绑定真实 Anki collection"),
        _row("Write authorization", "不是写入授权；未授予"),
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
