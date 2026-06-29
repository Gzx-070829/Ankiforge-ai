"""Read-only, non-executing provider preview projections."""

from dataclasses import dataclass, field

from .provider_consent import ProviderConsentRecord, ProviderSelection
from .provider_dry_run_request import (
    MAX_SOURCE_EXCERPT_PREVIEW_CHARS,
    ProviderDryRunRequest,
)
from .provider_error_display import ProviderErrorDisplay
from .user_provider_config import UserProviderProfile


_SENSITIVE_MARKERS = (
    "api_key",
    "api-key",
    "api key",
    "apikey",
    "authorization",
    "bearer",
    "password",
    "secret",
    "token",
    "headers",
    "raw exception",
    "raw response",
    "raw body",
    "full source text",
    "chunk text",
)


@dataclass(frozen=True)
class ProviderDryRunRequestPreview:
    """Safe projection of a dry-run request without its credential reference."""

    profile_id: str
    source_chunk_id: str
    source_title: str
    source_excerpt_preview: str = field(repr=False)
    source_excerpt_preview_length: int = field(repr=False)

    def __post_init__(self) -> None:
        _require_safe_display_text(self.profile_id, "profile_id")
        _require_safe_display_text(self.source_chunk_id, "source_chunk_id")
        _require_safe_display_text(self.source_title, "source_title")
        _require_text(self.source_excerpt_preview, "source_excerpt_preview")
        if len(self.source_excerpt_preview) > MAX_SOURCE_EXCERPT_PREVIEW_CHARS:
            raise ValueError(
                "source_excerpt_preview must not exceed 500 characters."
            )
        if (
            isinstance(self.source_excerpt_preview_length, bool)
            or not isinstance(self.source_excerpt_preview_length, int)
            or self.source_excerpt_preview_length
            != len(self.source_excerpt_preview)
        ):
            raise ValueError(
                "source_excerpt_preview_length must match the preview length."
            )

    @property
    def target_stage(self) -> str:
        return "knowledge_point_extraction"

    @property
    def will_send_full_source_text(self) -> bool:
        return False

    @property
    def will_write_to_anki(self) -> bool:
        return False

    @property
    def will_generate_cards(self) -> bool:
        return False

    @property
    def will_create_anki_notes(self) -> bool:
        return False

    def to_safe_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "source_chunk_id": self.source_chunk_id,
            "source_title": self.source_title,
            "source_excerpt_preview_length": self.source_excerpt_preview_length,
            "has_source_excerpt_preview": True,
            "target_stage": self.target_stage,
            "will_send_full_source_text": self.will_send_full_source_text,
            "will_write_to_anki": self.will_write_to_anki,
            "will_generate_cards": self.will_generate_cards,
            "will_create_anki_notes": self.will_create_anki_notes,
        }

    def to_user_visible_dict(self) -> dict:
        data = self.to_safe_dict()
        data["source_excerpt_preview"] = self.source_excerpt_preview
        return data


@dataclass(frozen=True)
class ReadOnlyProviderPreview:
    """UI-ready provider state projection with no execution authority."""

    profile_id: str
    provider_id: str
    provider_name: str
    model_name: str
    base_url: str
    sends_user_content: bool
    requires_explicit_consent: bool
    has_secret: bool = field(repr=False)
    consented_at_iso: str
    privacy_notice: str
    dry_run_preview: ProviderDryRunRequestPreview | None = field(
        default=None,
        repr=False,
    )
    error_display: ProviderErrorDisplay | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "provider_id",
            "provider_name",
            "model_name",
            "base_url",
            "privacy_notice",
        ):
            _require_safe_display_text(getattr(self, field_name), field_name)
        if self.sends_user_content is not True:
            raise ValueError("sends_user_content must be True.")
        if self.requires_explicit_consent is not True:
            raise ValueError("requires_explicit_consent must be True.")
        if type(self.has_secret) is not bool:
            raise ValueError("has_secret must be a bool.")
        if not isinstance(self.consented_at_iso, str):
            raise ValueError("consented_at_iso must be a string.")
        if self.consented_at_iso:
            _require_safe_display_text(
                self.consented_at_iso,
                "consented_at_iso",
            )
        if self.dry_run_preview is not None and not isinstance(
            self.dry_run_preview,
            ProviderDryRunRequestPreview,
        ):
            raise ValueError(
                "dry_run_preview must be ProviderDryRunRequestPreview or None."
            )
        if (
            self.dry_run_preview is not None
            and self.dry_run_preview.profile_id != self.profile_id
        ):
            raise ValueError("dry_run_preview profile must match provider profile.")
        if self.dry_run_preview is not None and not self.has_consent:
            raise ValueError("dry_run_preview requires explicit consent.")
        if self.error_display is not None and not isinstance(
            self.error_display,
            ProviderErrorDisplay,
        ):
            raise ValueError(
                "error_display must be ProviderErrorDisplay or None."
            )

    @property
    def has_consent(self) -> bool:
        return bool(self.consented_at_iso)

    @property
    def target_stage(self) -> str:
        return "knowledge_point_extraction"

    @property
    def will_write_to_anki(self) -> bool:
        return False

    @property
    def will_generate_cards(self) -> bool:
        return False

    @property
    def will_create_anki_notes(self) -> bool:
        return False

    def to_safe_dict(self) -> dict:
        return self._to_dict(include_excerpt=False)

    def to_user_visible_dict(self) -> dict:
        return self._to_dict(include_excerpt=True)

    def _to_dict(self, include_excerpt: bool) -> dict:
        if self.dry_run_preview is None:
            dry_run_data = None
        elif include_excerpt:
            dry_run_data = self.dry_run_preview.to_user_visible_dict()
        else:
            dry_run_data = self.dry_run_preview.to_safe_dict()
        return {
            "profile_id": self.profile_id,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "sends_user_content": self.sends_user_content,
            "requires_explicit_consent": self.requires_explicit_consent,
            "has_secret": self.has_secret,
            "has_consent": self.has_consent,
            "consented_at_iso": self.consented_at_iso,
            "privacy_notice": self.privacy_notice,
            "dry_run_preview": dry_run_data,
            "error_display": (
                self.error_display.to_safe_dict()
                if self.error_display is not None
                else None
            ),
            "target_stage": self.target_stage,
            "will_write_to_anki": self.will_write_to_anki,
            "will_generate_cards": self.will_generate_cards,
            "will_create_anki_notes": self.will_create_anki_notes,
        }


def build_read_only_provider_preview(
    profile: UserProviderProfile,
    selection: ProviderSelection,
    has_secret: bool,
    consent: ProviderConsentRecord | None = None,
    dry_run_request: ProviderDryRunRequest | None = None,
    error_display: ProviderErrorDisplay | None = None,
) -> ReadOnlyProviderPreview:
    """Project validated domain inputs into a non-executing preview."""
    if not isinstance(profile, UserProviderProfile):
        raise ValueError("profile must be UserProviderProfile.")
    if not isinstance(selection, ProviderSelection):
        raise ValueError("selection must be ProviderSelection.")
    if type(has_secret) is not bool:
        raise ValueError("has_secret must be a bool.")
    if not _profile_matches_selection(profile, selection):
        raise ValueError("profile must match provider selection.")
    if not (
        profile.sends_user_content is True
        and profile.requires_explicit_consent is True
        and selection.sends_user_content is True
        and selection.requires_explicit_consent is True
    ):
        raise ValueError("provider selection must require explicit consent.")
    if consent is not None:
        if not isinstance(consent, ProviderConsentRecord):
            raise ValueError("consent must be ProviderConsentRecord or None.")
        if not _selections_match(selection, consent.selection):
            raise ValueError("consent must match provider selection.")
        if not (
            consent.sends_user_content is True
            and consent.requires_explicit_consent is True
            and consent.has_explicit_consent is True
        ):
            raise ValueError("consent must be an explicit affirmative record.")
    if dry_run_request is not None:
        if not isinstance(dry_run_request, ProviderDryRunRequest):
            raise ValueError(
                "dry_run_request must be ProviderDryRunRequest or None."
            )
        if consent is None:
            raise ValueError("dry_run_request requires explicit consent.")
        if not _selections_match(selection, dry_run_request.selection):
            raise ValueError("dry_run_request must match provider selection.")
        if dry_run_request.consent != consent:
            raise ValueError("dry_run_request must match provider consent.")
        dry_run_preview = ProviderDryRunRequestPreview(
            profile_id=dry_run_request.selection.profile_id,
            source_chunk_id=dry_run_request.source_chunk_id,
            source_title=dry_run_request.source_title,
            source_excerpt_preview=dry_run_request.source_excerpt_preview,
            source_excerpt_preview_length=len(
                dry_run_request.source_excerpt_preview
            ),
        )
    else:
        dry_run_preview = None
    if error_display is not None and not isinstance(
        error_display,
        ProviderErrorDisplay,
    ):
        raise ValueError("error_display must be ProviderErrorDisplay or None.")
    return ReadOnlyProviderPreview(
        profile_id=profile.profile_id,
        provider_id=profile.provider_id,
        provider_name=profile.provider_name,
        model_name=profile.model_name,
        base_url=profile.base_url,
        sends_user_content=selection.sends_user_content,
        requires_explicit_consent=selection.requires_explicit_consent,
        has_secret=has_secret,
        consented_at_iso=(consent.consented_at.isoformat() if consent else ""),
        privacy_notice=profile.privacy_notice,
        dry_run_preview=dry_run_preview,
        error_display=error_display,
    )


def _profile_matches_selection(
    profile: UserProviderProfile,
    selection: ProviderSelection,
) -> bool:
    return all(
        getattr(profile, field_name) == getattr(selection, field_name)
        for field_name in (
            "profile_id",
            "provider_id",
            "provider_name",
            "model_name",
            "base_url",
        )
    )


def _selections_match(
    left: ProviderSelection,
    right: ProviderSelection,
) -> bool:
    return all(
        getattr(left, field_name) == getattr(right, field_name)
        for field_name in (
            "profile_id",
            "provider_id",
            "provider_name",
            "model_name",
            "base_url",
        )
    )


def _require_safe_display_text(value: str, field_name: str) -> None:
    _require_text(value, field_name)
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field_name} must not contain control characters.")
    lowered = value.lower()
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        raise ValueError(f"{field_name} contains unsafe display content.")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
