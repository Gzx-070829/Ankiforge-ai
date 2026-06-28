"""Provider selection and explicit-consent contracts for the new pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit

from .user_provider_config import UserProviderProfile


@dataclass(frozen=True)
class ProviderSelection:
    """Non-secret snapshot of the provider profile selected by a user."""

    profile_id: str
    provider_id: str
    provider_name: str
    model_name: str
    base_url: str

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "provider_id",
            "provider_name",
            "model_name",
        ):
            _require_text(getattr(self, field_name), field_name)
        _validate_base_url(self.base_url)

    @property
    def sends_user_content(self) -> bool:
        return True

    @property
    def requires_explicit_consent(self) -> bool:
        return True

    def to_safe_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "sends_user_content": self.sends_user_content,
            "requires_explicit_consent": self.requires_explicit_consent,
        }


@dataclass(frozen=True)
class ProviderConsentRecord:
    """Affirmative consent snapshot; absence of this record means no consent."""

    selection: ProviderSelection
    consent_text: str = field(repr=False)
    privacy_notice: str = field(repr=False)
    consented_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.selection, ProviderSelection):
            raise ValueError("selection must be ProviderSelection.")
        _require_text(self.consent_text, "consent_text")
        _require_text(self.privacy_notice, "privacy_notice")
        if not isinstance(self.consented_at, datetime):
            raise ValueError("consented_at must be a timezone-aware datetime.")
        try:
            offset = self.consented_at.utcoffset()
        except Exception as error:
            raise ValueError(
                "consented_at must be a timezone-aware datetime."
            ) from None
        if self.consented_at.tzinfo is None or offset is None:
            raise ValueError("consented_at must be a timezone-aware datetime.")

    @property
    def sends_user_content(self) -> bool:
        return True

    @property
    def requires_explicit_consent(self) -> bool:
        return True

    @property
    def has_explicit_consent(self) -> bool:
        return True

    def to_safe_dict(self) -> dict:
        return {
            "selection": self.selection.to_safe_dict(),
            "consent_text": self.consent_text,
            "privacy_notice": self.privacy_notice,
            "consented_at": self.consented_at.isoformat(),
            "sends_user_content": self.sends_user_content,
            "requires_explicit_consent": self.requires_explicit_consent,
            "has_explicit_consent": self.has_explicit_consent,
        }


def create_provider_selection_from_profile(
    profile: UserProviderProfile,
) -> ProviderSelection:
    """Create a non-secret selection snapshot from a validated profile."""
    if not isinstance(profile, UserProviderProfile):
        raise ValueError("profile must be UserProviderProfile.")
    return ProviderSelection(
        profile_id=profile.profile_id,
        provider_id=profile.provider_id,
        provider_name=profile.provider_name,
        model_name=profile.model_name,
        base_url=profile.base_url,
    )


def create_provider_consent_record(
    selection: ProviderSelection,
    consent_text: str,
    privacy_notice: str,
    consented_at: datetime,
) -> ProviderConsentRecord:
    """Create affirmative consent only from fully explicit caller input."""
    return ProviderConsentRecord(
        selection=selection,
        consent_text=consent_text,
        privacy_notice=privacy_notice,
        consented_at=consented_at,
    )


def _validate_base_url(value: str) -> None:
    _require_text(value, "base_url")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        username = parsed.username
        password = parsed.password
    except ValueError:
        raise ValueError("base_url must be a valid HTTP or HTTPS URL.") from None

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("base_url must use http or https.")
    if not parsed.netloc or not hostname:
        raise ValueError("base_url must include a hostname.")
    if "@" in parsed.netloc or username is not None or password is not None:
        raise ValueError("base_url must not include embedded credentials.")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
