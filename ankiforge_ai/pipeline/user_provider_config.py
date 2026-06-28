"""Safe user-facing provider profile for the v0.6 pipeline boundary."""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

from .openai_compatible_provider import OpenAICompatibleProviderConfig


@dataclass(frozen=True)
class UserProviderProfile:
    """Non-secret settings for one user-configured provider profile."""

    profile_id: str
    provider_id: str
    provider_name: str
    model_name: str
    base_url: str
    privacy_notice: str
    timeout_seconds: Optional[float] = 60.0

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "provider_id",
            "provider_name",
            "model_name",
            "privacy_notice",
        ):
            _require_text(getattr(self, field_name), field_name)
        _validate_base_url(self.base_url)
        if self.timeout_seconds is not None and (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive or None.")

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
            "privacy_notice": self.privacy_notice,
            "timeout_seconds": self.timeout_seconds,
            "sends_user_content": self.sends_user_content,
            "requires_explicit_consent": self.requires_explicit_consent,
        }


def create_openai_compatible_config_from_user_profile(
    profile: UserProviderProfile,
    api_key: str,
) -> OpenAICompatibleProviderConfig:
    """Combine a non-secret profile with an explicitly supplied runtime key."""
    if not isinstance(profile, UserProviderProfile):
        raise ValueError("profile must be UserProviderProfile.")
    return OpenAICompatibleProviderConfig(
        provider_id=profile.provider_id,
        provider_name=profile.provider_name,
        model_name=profile.model_name,
        base_url=profile.base_url,
        api_key=api_key,
        privacy_notice=profile.privacy_notice,
        timeout_seconds=profile.timeout_seconds,
    )


def _validate_base_url(value: str) -> None:
    _require_text(value, "base_url")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        username = parsed.username
        password = parsed.password
    except ValueError as error:
        raise ValueError("base_url must be a valid HTTP or HTTPS URL.") from error

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("base_url must use http or https.")
    if not parsed.netloc or not hostname:
        raise ValueError("base_url must include a hostname.")
    if "@" in parsed.netloc or username is not None or password is not None:
        raise ValueError("base_url must not include embedded credentials.")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
