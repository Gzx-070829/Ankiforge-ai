"""Build a non-authorizing send disclosure from a valid local draft preview."""

from dataclasses import dataclass

from .provider_profile_draft_helpers import (
    PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
    ProviderProfileDraftDisplayRow,
)
from .provider_profile_draft_preview_adapter import (
    VALID_DRAFT_SUMMARY_MESSAGE,
    ProviderProfileDraftReadOnlyPreview,
)


DISCLOSURE_SUMMARY_MESSAGE = (
    "仅说明未来真实 provider 流程的发送边界；当前仍是本地预览。"
)


@dataclass(frozen=True)
class ProviderProfileDraftSendDisclosure:
    """Current-versus-future disclosure with no consent or runtime authority."""

    summary_message: str
    current_rows: tuple[ProviderProfileDraftDisplayRow, ...]
    future_rows: tuple[ProviderProfileDraftDisplayRow, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.summary_message, str) or not self.summary_message.strip():
            raise ValueError("summary_message must be a non-empty string.")
        for rows_name, rows in (
            ("current_rows", self.current_rows),
            ("future_rows", self.future_rows),
        ):
            if not isinstance(rows, tuple) or not all(
                isinstance(row, ProviderProfileDraftDisplayRow) for row in rows
            ):
                raise ValueError(f"{rows_name} has an invalid row type.")

    def to_safe_dict(self) -> dict:
        """Return fixed disclosure metadata without copying draft values."""
        return {
            "summary_message": self.summary_message,
            "current_rows": tuple(row.to_safe_dict() for row in self.current_rows),
            "future_rows": tuple(row.to_safe_dict() for row in self.future_rows),
        }


def build_provider_profile_draft_send_disclosure(
    preview: ProviderProfileDraftReadOnlyPreview,
) -> ProviderProfileDraftSendDisclosure | None:
    """Disclose future send semantics only for a valid PR3 local preview."""
    if not isinstance(preview, ProviderProfileDraftReadOnlyPreview):
        raise ValueError("preview must be ProviderProfileDraftReadOnlyPreview.")
    if preview.is_empty or not preview.is_valid:
        return None

    _validate_valid_preview(preview)
    return ProviderProfileDraftSendDisclosure(
        summary_message=DISCLOSURE_SUMMARY_MESSAGE,
        current_rows=_current_rows(),
        future_rows=_future_rows(),
    )


def _validate_valid_preview(preview: ProviderProfileDraftReadOnlyPreview) -> None:
    if preview.summary_message != VALID_DRAFT_SUMMARY_MESSAGE:
        raise ValueError("valid preview must retain the PR3 summary boundary.")
    if preview.validation_errors:
        raise ValueError("valid preview must not contain validation errors.")

    expected_provider_labels = (
        "Provider",
        "Model",
        "Base URL",
        "Privacy notice",
        "Target stage",
    )
    if tuple(row.label for row in preview.provider_rows) != expected_provider_labels:
        raise ValueError("valid preview has an invalid provider row shape.")
    if _row_value(preview.provider_rows, "Target stage") != (
        PROVIDER_PROFILE_DRAFT_TARGET_STAGE
    ):
        raise ValueError("valid preview has an invalid target stage.")

    expected_status = (
        ("Preview source", "仅本地草稿"),
        ("Activation status", "未激活"),
        ("Provider verification", "未执行"),
        ("Consent status", "不适用（未激活）"),
        ("Will save settings", "否"),
        ("Will send content", "否"),
        ("Will call provider", "否"),
        ("Will generate cards", "否"),
        ("Will write to Anki", "否"),
    )
    if tuple((row.label, row.value) for row in preview.status_rows) != expected_status:
        raise ValueError("valid preview must retain the fixed PR3 safety boundary.")


def _current_rows() -> tuple[ProviderProfileDraftDisplayRow, ...]:
    return (
        _row("当前操作", "仅本地预览"),
        _row("当前保存设置", "否"),
        _row("当前接收 API key", "否"),
        _row("当前发送资料", "否"),
        _row("当前调用 provider", "否"),
        _row("当前读取源资料 / Anki 内容", "否"),
        _row("当前创建 consent", "否（未请求、未记录）"),
        _row("当前生成卡片", "否"),
        _row("当前写入 Anki", "否"),
    )


def _future_rows() -> tuple[ProviderProfileDraftDisplayRow, ...]:
    return (
        _row("未来发送对象", "上方草稿中的 Provider / Base URL"),
        _row("未来发送内容", "仅用户明确选择的短预览"),
        _row("未来发送前", "必须再次明确同意"),
        _row("Target stage", PROVIDER_PROFILE_DRAFT_TARGET_STAGE),
        _row("披露边界", "本披露不构成 consent 或执行授权"),
        _row("Provider 状态", "本披露不代表 provider 已验证、激活或可运行"),
    )


def _row(label: str, value: str) -> ProviderProfileDraftDisplayRow:
    return ProviderProfileDraftDisplayRow(label=label, value=value)


def _row_value(
    rows: tuple[ProviderProfileDraftDisplayRow, ...],
    label: str,
) -> str:
    return next(row.value for row in rows if row.label == label)
