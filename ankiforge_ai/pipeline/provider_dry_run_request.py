"""Consent-gated request model for a future provider knowledge-point dry run."""

from dataclasses import dataclass, field

from .provider_consent import ProviderConsentRecord, ProviderSelection
from .provider_secret_store import ProviderSecretRef


MAX_SOURCE_EXCERPT_PREVIEW_CHARS = 500


@dataclass(frozen=True)
class ProviderDryRunRequest:
    """Validated request description without credentials or execution behavior."""

    selection: ProviderSelection
    consent: ProviderConsentRecord
    secret_ref: ProviderSecretRef = field(repr=False)
    source_chunk_id: str
    source_title: str
    source_excerpt_preview: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.selection, ProviderSelection):
            raise ValueError("selection must be ProviderSelection.")
        if not isinstance(self.consent, ProviderConsentRecord):
            raise ValueError("consent must be ProviderConsentRecord.")
        if not isinstance(self.secret_ref, ProviderSecretRef):
            raise ValueError("secret_ref must be ProviderSecretRef.")
        if not _selections_match(self.selection, self.consent.selection):
            raise ValueError("consent selection must match request selection.")
        if not (
            self.selection.sends_user_content is True
            and self.selection.requires_explicit_consent is True
        ):
            raise ValueError("selection must require consent for user content.")
        if not (
            self.consent.sends_user_content is True
            and self.consent.requires_explicit_consent is True
            and self.consent.has_explicit_consent is True
        ):
            raise ValueError("consent must be an explicit affirmative record.")
        if self.secret_ref.profile_id != self.selection.profile_id:
            raise ValueError("secret_ref profile must match request selection.")
        _require_text(self.source_chunk_id, "source_chunk_id")
        _require_text(self.source_title, "source_title")
        _require_text(self.source_excerpt_preview, "source_excerpt_preview")
        if len(self.source_excerpt_preview) > MAX_SOURCE_EXCERPT_PREVIEW_CHARS:
            raise ValueError(
                "source_excerpt_preview must not exceed 500 characters."
            )

    def to_safe_dict(self) -> dict:
        return {
            "selection": self.selection.to_safe_dict(),
            "consent": self.consent.to_safe_dict(),
            "source_chunk_id": self.source_chunk_id,
            "source_title": self.source_title,
            "source_excerpt_preview": self.source_excerpt_preview,
            "target_stage": "knowledge_point_extraction",
        }


def create_provider_dry_run_request(
    selection: ProviderSelection,
    consent: ProviderConsentRecord,
    secret_ref: ProviderSecretRef,
    source_chunk_id: str,
    source_title: str,
    source_excerpt_preview: str,
) -> ProviderDryRunRequest:
    """Build a request description from fully explicit, already-created inputs."""
    return ProviderDryRunRequest(
        selection=selection,
        consent=consent,
        secret_ref=secret_ref,
        source_chunk_id=source_chunk_id,
        source_title=source_title,
        source_excerpt_preview=source_excerpt_preview,
    )


def _selections_match(
    request_selection: ProviderSelection,
    consent_selection: ProviderSelection,
) -> bool:
    return all(
        getattr(request_selection, field_name)
        == getattr(consent_selection, field_name)
        for field_name in (
            "profile_id",
            "provider_id",
            "provider_name",
            "model_name",
            "base_url",
        )
    )


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
