"""Pure presentation helpers for the read-only provider preview UI."""

from dataclasses import dataclass, field

from ..pipeline.provider_preview import ReadOnlyProviderPreview


EMPTY_PROVIDER_PREVIEW_MESSAGE = "新 pipeline provider 尚未配置"
MAX_PROVIDER_EXCERPT_DISPLAY_CHARS = 500


@dataclass(frozen=True)
class ProviderPreviewDisplayRow:
    """One explicitly whitelisted label/value pair for the UI."""

    label: str
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("label must be a non-empty string.")
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("value must be a non-empty string.")

    def to_safe_dict(self) -> dict:
        return {"label": self.label, "value": self.value}


@dataclass(frozen=True)
class ProviderPreviewViewData:
    """UI-ready rows with the user-visible excerpt kept out of safe output."""

    is_empty: bool
    empty_state_message: str
    provider_rows: tuple[ProviderPreviewDisplayRow, ...]
    safety_rows: tuple[ProviderPreviewDisplayRow, ...]
    dry_run_rows: tuple[ProviderPreviewDisplayRow, ...]
    source_excerpt_preview: str = field(repr=False)
    error_rows: tuple[ProviderPreviewDisplayRow, ...] = ()

    def __post_init__(self) -> None:
        if type(self.is_empty) is not bool:
            raise ValueError("is_empty must be a bool.")
        if not isinstance(self.empty_state_message, str):
            raise ValueError("empty_state_message must be a string.")
        if not isinstance(self.source_excerpt_preview, str):
            raise ValueError("source_excerpt_preview must be a string.")
        if len(self.source_excerpt_preview) > MAX_PROVIDER_EXCERPT_DISPLAY_CHARS:
            raise ValueError("source_excerpt_preview exceeds the UI display limit.")
        for rows_name, rows in (
            ("provider_rows", self.provider_rows),
            ("safety_rows", self.safety_rows),
            ("dry_run_rows", self.dry_run_rows),
            ("error_rows", self.error_rows),
        ):
            if not isinstance(rows, tuple) or not all(
                isinstance(row, ProviderPreviewDisplayRow) for row in rows
            ):
                raise ValueError(
                    f"{rows_name} must be a tuple of ProviderPreviewDisplayRow."
                )

    def to_safe_dict(self) -> dict:
        return {
            "is_empty": self.is_empty,
            "empty_state_message": self.empty_state_message,
            "provider_rows": tuple(row.to_safe_dict() for row in self.provider_rows),
            "safety_rows": tuple(row.to_safe_dict() for row in self.safety_rows),
            "dry_run_rows": tuple(row.to_safe_dict() for row in self.dry_run_rows),
            "has_source_excerpt_preview": bool(self.source_excerpt_preview),
            "source_excerpt_preview_length": len(self.source_excerpt_preview),
            "error_rows": tuple(row.to_safe_dict() for row in self.error_rows),
        }


def build_provider_preview_view_data(
    preview: ReadOnlyProviderPreview | None,
) -> ProviderPreviewViewData:
    """Map one safe projection to an explicit UI whitelist without execution."""
    if preview is None:
        return ProviderPreviewViewData(
            is_empty=True,
            empty_state_message=EMPTY_PROVIDER_PREVIEW_MESSAGE,
            provider_rows=(),
            safety_rows=_fixed_no_write_rows("knowledge_point_extraction"),
            dry_run_rows=(),
            source_excerpt_preview="",
        )
    if not isinstance(preview, ReadOnlyProviderPreview):
        raise ValueError("preview must be ReadOnlyProviderPreview or None.")
    if preview.target_stage != "knowledge_point_extraction":
        raise ValueError("preview target_stage must be knowledge_point_extraction.")
    if any(
        (
            preview.will_write_to_anki,
            preview.will_generate_cards,
            preview.will_create_anki_notes,
        )
    ):
        raise ValueError("provider preview must remain read-only and non-writing.")

    provider_rows = (
        _row("Provider", preview.provider_name),
        _row("Provider ID", preview.provider_id),
        _row("Model", preview.model_name),
        _row("Base URL", preview.base_url),
        _row("Privacy notice", preview.privacy_notice),
    )
    safety_rows = (
        _row(
            "Credential status",
            "已配置，未验证" if preview.has_secret else "未配置，未验证",
        ),
        _row("Consent status", "已确认" if preview.has_consent else "未确认"),
        _row("Consent time", preview.consented_at_iso or "未记录"),
        _row("Sends user content", _yes_no(preview.sends_user_content)),
        _row(
            "Requires explicit consent",
            _yes_no(preview.requires_explicit_consent),
        ),
    ) + _fixed_no_write_rows(preview.target_stage)

    dry_run_preview = preview.dry_run_preview
    if dry_run_preview is None:
        dry_run_rows = (_row("Dry-run request", "尚未准备"),)
        source_excerpt_preview = ""
    else:
        dry_run_rows = (
            _row("Dry-run request", "已准备，仅供只读预览"),
            _row("Source title", dry_run_preview.source_title),
            _row("Source chunk ID", dry_run_preview.source_chunk_id),
            _row(
                "Excerpt length",
                str(dry_run_preview.source_excerpt_preview_length),
            ),
            _row(
                "Will send full source",
                _yes_no(dry_run_preview.will_send_full_source_text),
            ),
        )
        source_excerpt_preview = truncate_provider_preview_excerpt(
            dry_run_preview.source_excerpt_preview
        )

    if preview.error_display is None:
        error_rows = ()
    else:
        error = preview.error_display
        error_rows = (
            _row("Error type", error.kind.value),
            _row("Title", error.user_title),
            _row("Message", error.user_message),
            _row("Suggested action", error.suggested_action),
            _row("Retryable", _yes_no(error.retryable)),
            _row("Diagnostic code", error.safe_diagnostic_code),
        )

    return ProviderPreviewViewData(
        is_empty=False,
        empty_state_message="",
        provider_rows=provider_rows,
        safety_rows=safety_rows,
        dry_run_rows=dry_run_rows,
        source_excerpt_preview=source_excerpt_preview,
        error_rows=error_rows,
    )


def truncate_provider_preview_excerpt(
    text: str,
    max_chars: int = MAX_PROVIDER_EXCERPT_DISPLAY_CHARS,
) -> str:
    """Defensively cap user-visible preview text without exposing the remainder."""
    if not isinstance(text, str):
        raise ValueError("text must be a string.")
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars <= 0:
        raise ValueError("max_chars must be a positive integer.")
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3] + "..."


def _fixed_no_write_rows(target_stage: str) -> tuple[ProviderPreviewDisplayRow, ...]:
    return (
        _row("Target stage", target_stage),
        _row("Will write to Anki", "否"),
        _row("Will generate cards", "否"),
        _row("Will create Anki notes", "否"),
    )


def _row(label: str, value: object) -> ProviderPreviewDisplayRow:
    return ProviderPreviewDisplayRow(label=label, value=str(value))


def _yes_no(value: bool) -> str:
    return "是" if value else "否"
