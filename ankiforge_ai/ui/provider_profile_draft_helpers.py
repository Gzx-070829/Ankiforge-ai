"""Pure presentation helpers for a non-persistent provider profile draft."""

from dataclasses import dataclass, field

from ..pipeline.user_provider_config import UserProviderProfile


EMPTY_PROVIDER_PROFILE_DRAFT_MESSAGE = "尚未填写本地 provider 草稿"
PROVIDER_PROFILE_DRAFT_TARGET_STAGE = "knowledge_point_extraction"
_DRAFT_PROFILE_ID = "local-ui-draft-preview"


@dataclass(frozen=True)
class ProviderProfileDraftInput:
    """Non-sensitive values owned only by one open draft dialog."""

    provider: str = field(default="", repr=False)
    model: str = field(default="", repr=False)
    base_url: str = field(default="", repr=False)
    privacy_notice: str = field(default="", repr=False)
    target_stage: str = PROVIDER_PROFILE_DRAFT_TARGET_STAGE

    def __post_init__(self) -> None:
        for field_name in (
            "provider",
            "model",
            "base_url",
            "privacy_notice",
            "target_stage",
        ):
            if not isinstance(getattr(self, field_name), str):
                raise ValueError(f"{field_name} must be a string.")
        if self.target_stage != PROVIDER_PROFILE_DRAFT_TARGET_STAGE:
            raise ValueError(
                "target_stage must be knowledge_point_extraction."
            )

    def to_safe_dict(self) -> dict:
        """Summarize draft shape without copying user-entered values."""
        return {
            "provider_present": bool(self.provider.strip()),
            "provider_length": len(self.provider),
            "model_present": bool(self.model.strip()),
            "model_length": len(self.model),
            "base_url_present": bool(self.base_url.strip()),
            "base_url_length": len(self.base_url),
            "privacy_notice_present": bool(self.privacy_notice.strip()),
            "privacy_notice_length": len(self.privacy_notice),
            "target_stage": self.target_stage,
        }


@dataclass(frozen=True)
class ProviderProfileDraftDisplayRow:
    """One explicitly whitelisted label/value pair for the local UI."""

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
class ProviderProfileDraftValidationError:
    """A local field error that never includes the rejected value."""

    field_name: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.field_name, str) or not self.field_name.strip():
            raise ValueError("field_name must be a non-empty string.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string.")

    def to_safe_dict(self) -> dict:
        return {"field_name": self.field_name, "message": self.message}


@dataclass(frozen=True)
class ProviderProfileDraftViewData:
    """UI-ready local preview with no persistence or execution authority."""

    is_empty: bool
    is_valid: bool
    empty_state_message: str
    profile_rows: tuple[ProviderProfileDraftDisplayRow, ...]
    safety_rows: tuple[ProviderProfileDraftDisplayRow, ...]
    validation_errors: tuple[ProviderProfileDraftValidationError, ...]

    def __post_init__(self) -> None:
        if type(self.is_empty) is not bool:
            raise ValueError("is_empty must be a bool.")
        if type(self.is_valid) is not bool:
            raise ValueError("is_valid must be a bool.")
        if not isinstance(self.empty_state_message, str):
            raise ValueError("empty_state_message must be a string.")
        for rows_name, rows, row_type in (
            ("profile_rows", self.profile_rows, ProviderProfileDraftDisplayRow),
            ("safety_rows", self.safety_rows, ProviderProfileDraftDisplayRow),
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
        return {
            "is_empty": self.is_empty,
            "is_valid": self.is_valid,
            "empty_state_message": self.empty_state_message,
            "profile_rows": tuple(row.to_safe_dict() for row in self.profile_rows),
            "safety_rows": tuple(row.to_safe_dict() for row in self.safety_rows),
            "validation_errors": tuple(
                error.to_safe_dict() for error in self.validation_errors
            ),
        }


def build_provider_profile_draft_view_data(
    draft: ProviderProfileDraftInput | None,
) -> ProviderProfileDraftViewData:
    """Validate and present one in-memory draft without activating it."""
    if draft is None:
        draft = ProviderProfileDraftInput()
    if not isinstance(draft, ProviderProfileDraftInput):
        raise ValueError("draft must be ProviderProfileDraftInput or None.")

    normalized = {
        "provider": draft.provider.strip(),
        "model": draft.model.strip(),
        "base_url": draft.base_url.strip(),
        "privacy_notice": draft.privacy_notice.strip(),
    }
    if not any(normalized.values()):
        return ProviderProfileDraftViewData(
            is_empty=True,
            is_valid=False,
            empty_state_message=EMPTY_PROVIDER_PROFILE_DRAFT_MESSAGE,
            profile_rows=(),
            safety_rows=_fixed_safety_rows(),
            validation_errors=(),
        )

    errors = _required_field_errors(normalized)
    if not errors:
        error = _profile_validation_error(normalized)
        if error is not None:
            errors.append(error)
    if errors:
        return ProviderProfileDraftViewData(
            is_empty=False,
            is_valid=False,
            empty_state_message="",
            profile_rows=(),
            safety_rows=_fixed_safety_rows(),
            validation_errors=tuple(errors),
        )

    return ProviderProfileDraftViewData(
        is_empty=False,
        is_valid=True,
        empty_state_message="",
        profile_rows=(
            _row("Provider", normalized["provider"]),
            _row("Model", normalized["model"]),
            _row("Base URL", normalized["base_url"]),
            _row("Privacy notice", normalized["privacy_notice"]),
            _row("Target stage", PROVIDER_PROFILE_DRAFT_TARGET_STAGE),
        ),
        safety_rows=_fixed_safety_rows(),
        validation_errors=(),
    )


def _required_field_errors(
    normalized: dict[str, str],
) -> list[ProviderProfileDraftValidationError]:
    labels = {
        "provider": "Provider",
        "model": "Model",
        "base_url": "Base URL",
        "privacy_notice": "Privacy notice",
    }
    return [
        ProviderProfileDraftValidationError(
            field_name=field_name,
            message=f"{label} 不能为空。",
        )
        for field_name, label in labels.items()
        if not normalized[field_name]
    ]


def _profile_validation_error(
    normalized: dict[str, str],
) -> ProviderProfileDraftValidationError | None:
    try:
        UserProviderProfile(
            profile_id=_DRAFT_PROFILE_ID,
            provider_id=normalized["provider"],
            provider_name=normalized["provider"],
            model_name=normalized["model"],
            base_url=normalized["base_url"],
            privacy_notice=normalized["privacy_notice"],
            timeout_seconds=None,
        )
    except ValueError as error:
        message = str(error)
        if "embedded credentials" in message:
            safe_message = "Base URL 不能包含用户名或密码。"
        elif "must use http or https" in message:
            safe_message = "Base URL 必须使用 HTTP 或 HTTPS。"
        elif "must include a hostname" in message:
            safe_message = "Base URL 必须包含有效主机名。"
        else:
            safe_message = "Base URL 格式无效。"
        return ProviderProfileDraftValidationError(
            field_name="base_url",
            message=safe_message,
        )
    return None


def _fixed_safety_rows() -> tuple[ProviderProfileDraftDisplayRow, ...]:
    return (
        _row("Draft lifetime", "仅当前弹窗，关闭后丢弃"),
        _row("Will save settings", "否"),
        _row("Will send user content", "否"),
        _row("Will call provider", "否"),
        _row("Will generate cards", "否"),
        _row("Will write to Anki", "否"),
    )


def _row(label: str, value: str) -> ProviderProfileDraftDisplayRow:
    return ProviderProfileDraftDisplayRow(label=label, value=value)
