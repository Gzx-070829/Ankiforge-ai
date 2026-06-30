"""Adapt a validated local draft view into a read-only-style UI summary."""

from dataclasses import dataclass

from .provider_profile_draft_helpers import (
    PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
    ProviderProfileDraftDisplayRow,
    ProviderProfileDraftValidationError,
    ProviderProfileDraftViewData,
)


VALID_DRAFT_SUMMARY_MESSAGE = (
    "格式有效 ≠ provider 已验证；安全摘要 ≠ runtime preview；"
    "本地草稿 ≠ 已保存配置。"
)
INVALID_DRAFT_SUMMARY_MESSAGE = "草稿未通过本地格式校验。"


@dataclass(frozen=True)
class ProviderProfileDraftReadOnlyPreview:
    """A presentation-only summary with no runtime provider authority."""

    is_empty: bool
    is_valid: bool
    summary_message: str
    provider_rows: tuple[ProviderProfileDraftDisplayRow, ...]
    status_rows: tuple[ProviderProfileDraftDisplayRow, ...]
    validation_errors: tuple[ProviderProfileDraftValidationError, ...]

    def __post_init__(self) -> None:
        if type(self.is_empty) is not bool:
            raise ValueError("is_empty must be a bool.")
        if type(self.is_valid) is not bool:
            raise ValueError("is_valid must be a bool.")
        if not isinstance(self.summary_message, str) or not self.summary_message.strip():
            raise ValueError("summary_message must be a non-empty string.")
        for rows_name, rows, row_type in (
            ("provider_rows", self.provider_rows, ProviderProfileDraftDisplayRow),
            ("status_rows", self.status_rows, ProviderProfileDraftDisplayRow),
            (
                "validation_errors",
                self.validation_errors,
                ProviderProfileDraftValidationError,
            ),
        ):
            if not isinstance(rows, tuple) or not all(
                isinstance(row, row_type) for row in rows
            ):
                raise ValueError(f"{rows_name} has an invalid row type.")

    def to_safe_dict(self) -> dict:
        """Return metadata without copying complete user-entered values."""
        return {
            "is_empty": self.is_empty,
            "is_valid": self.is_valid,
            "summary_message": self.summary_message,
            "provider_rows": tuple(row.to_safe_dict() for row in self.provider_rows),
            "status_rows": tuple(row.to_safe_dict() for row in self.status_rows),
            "validation_errors": tuple(
                error.to_safe_dict() for error in self.validation_errors
            ),
        }


def build_provider_profile_draft_read_only_preview(
    view_data: ProviderProfileDraftViewData,
) -> ProviderProfileDraftReadOnlyPreview:
    """Build a local read-only-style summary from one validated PR2 view."""
    if not isinstance(view_data, ProviderProfileDraftViewData):
        raise ValueError("view_data must be ProviderProfileDraftViewData.")
    _validate_view_data_state(view_data)

    if view_data.is_empty:
        summary_message = view_data.empty_state_message
        provider_rows = ()
    elif view_data.is_valid:
        summary_message = VALID_DRAFT_SUMMARY_MESSAGE
        provider_rows = view_data.profile_rows
    else:
        summary_message = INVALID_DRAFT_SUMMARY_MESSAGE
        provider_rows = ()

    return ProviderProfileDraftReadOnlyPreview(
        is_empty=view_data.is_empty,
        is_valid=view_data.is_valid,
        summary_message=summary_message,
        provider_rows=provider_rows,
        status_rows=_fixed_status_rows(),
        validation_errors=view_data.validation_errors,
    )


def _validate_view_data_state(view_data: ProviderProfileDraftViewData) -> None:
    expected_safety = (
        ("Draft lifetime", "仅当前弹窗，关闭后丢弃"),
        ("Will save settings", "否"),
        ("Will send user content", "否"),
        ("Will call provider", "否"),
        ("Will generate cards", "否"),
        ("Will write to Anki", "否"),
    )
    if tuple(
        (row.label, row.value) for row in view_data.safety_rows
    ) != expected_safety:
        raise ValueError("view_data must retain the fixed PR2 safety boundary.")

    if view_data.is_empty:
        if view_data.is_valid or view_data.profile_rows or view_data.validation_errors:
            raise ValueError("empty view_data has inconsistent state.")
        return

    if view_data.is_valid:
        expected_labels = (
            "Provider",
            "Model",
            "Base URL",
            "Privacy notice",
            "Target stage",
        )
        if tuple(row.label for row in view_data.profile_rows) != expected_labels:
            raise ValueError("valid view_data has an invalid provider row shape.")
        if view_data.validation_errors:
            raise ValueError("valid view_data must not contain validation errors.")
        if _row_value(view_data.profile_rows, "Target stage") != (
            PROVIDER_PROFILE_DRAFT_TARGET_STAGE
        ):
            raise ValueError("valid view_data has an invalid target stage.")
        return

    if view_data.profile_rows or not view_data.validation_errors:
        raise ValueError("invalid view_data has inconsistent state.")


def _fixed_status_rows() -> tuple[ProviderProfileDraftDisplayRow, ...]:
    return (
        _row("Preview source", "仅本地草稿"),
        _row("Activation status", "未激活"),
        _row("Provider verification", "未执行"),
        _row("Consent status", "不适用（未激活）"),
        _row("Will save settings", "否"),
        _row("Will send content", "否"),
        _row("Will call provider", "否"),
        _row("Will generate cards", "否"),
        _row("Will write to Anki", "否"),
    )


def _row(label: str, value: str) -> ProviderProfileDraftDisplayRow:
    return ProviderProfileDraftDisplayRow(label=label, value=value)


def _row_value(
    rows: tuple[ProviderProfileDraftDisplayRow, ...],
    label: str,
) -> str:
    return next(row.value for row in rows if row.label == label)
