"""Consent-gated OpenAI-compatible executor for provider dry runs."""

import hashlib
from dataclasses import dataclass, field

from .ai_extraction_service import KnowledgePointExtractionOutcome
from .models import SourceChunk
from .openai_compatible_provider import OpenAICompatibleTransport
from .provider_consent import ProviderConsentRecord, ProviderSelection
from .provider_dry_run_execution import (
    ProviderDryRunExecutionInput,
    ProviderDryRunExecutionResult,
    ProviderDryRunExecutorOutcome,
    execute_provider_dry_run_with_boundary,
)
from .provider_error_display import ProviderErrorKind
from .provider_factory import (
    create_openai_compatible_knowledge_point_extractor,
)
from .provider_secret_store import (
    ProviderSecretRef,
    ProviderSecretStore,
    ProviderSecretValue,
)
from .user_provider_config import (
    UserProviderProfile,
    create_openai_compatible_config_from_user_profile,
)


_TARGET_STAGE = "knowledge_point_extraction"


@dataclass(frozen=True)
class OpenAICompatibleProviderDryRunExecutor:
    """Real-capable executor whose dependencies must all be explicit."""

    profile: UserProviderProfile = field(repr=False)
    secret_store: ProviderSecretStore = field(repr=False)
    transport: OpenAICompatibleTransport = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.profile, UserProviderProfile):
            raise ValueError("profile must be UserProviderProfile.")
        if not isinstance(self.secret_store, ProviderSecretStore):
            raise ValueError("secret_store must implement ProviderSecretStore.")
        if not isinstance(self.transport, OpenAICompatibleTransport):
            raise ValueError("transport must implement OpenAICompatibleTransport.")

    def execute(
        self,
        execution_input: ProviderDryRunExecutionInput,
    ) -> ProviderDryRunExecutorOutcome:
        if not isinstance(execution_input, ProviderDryRunExecutionInput):
            raise ValueError(
                "execution_input must be ProviderDryRunExecutionInput."
            )
        _validate_executor_boundary(self.profile, execution_input)

        secret_value = self.secret_store.load_secret(
            execution_input.request.secret_ref
        )
        if secret_value is None:
            return ProviderDryRunExecutorOutcome(
                error_kind=ProviderErrorKind.AUTH_ERROR
            )
        if not isinstance(secret_value, ProviderSecretValue):
            return ProviderDryRunExecutorOutcome(
                error_kind=ProviderErrorKind.UNKNOWN_ERROR
            )

        extraction_outcome = _extract_inside_secret_reveal_boundary(
            profile=self.profile,
            secret_value=secret_value,
            transport=self.transport,
            chunk=_build_preview_source_chunk(execution_input),
        )
        return _normalize_extraction_outcome(extraction_outcome)


def execute_openai_compatible_provider_dry_run_with_boundary(
    execution_input: ProviderDryRunExecutionInput,
    executor: OpenAICompatibleProviderDryRunExecutor,
) -> ProviderDryRunExecutionResult:
    """Execute the real-capable executor only through the PR7a boundary."""
    if not isinstance(executor, OpenAICompatibleProviderDryRunExecutor):
        raise ValueError(
            "executor must be OpenAICompatibleProviderDryRunExecutor."
        )
    return execute_provider_dry_run_with_boundary(execution_input, executor)


def _extract_inside_secret_reveal_boundary(
    profile: UserProviderProfile,
    secret_value: ProviderSecretValue,
    transport: OpenAICompatibleTransport,
    chunk: SourceChunk,
) -> KnowledgePointExtractionOutcome:
    """Reveal the secret only here and keep all credential consumers local."""
    api_key = secret_value.reveal()
    config = None
    extractor = None
    try:
        config = create_openai_compatible_config_from_user_profile(
            profile,
            api_key,
        )
        extractor = create_openai_compatible_knowledge_point_extractor(
            config,
            transport=transport,
            wrap_safe=True,
        )
        return extractor.extract_from_chunk(chunk)
    finally:
        extractor = None
        config = None
        api_key = None


def _validate_executor_boundary(
    profile: UserProviderProfile,
    execution_input: ProviderDryRunExecutionInput,
) -> None:
    request = execution_input.request
    if execution_input.target_stage != _TARGET_STAGE:
        raise ValueError("target stage must be knowledge_point_extraction.")
    if not isinstance(request.selection, ProviderSelection):
        raise ValueError("request selection must be ProviderSelection.")
    if not isinstance(request.consent, ProviderConsentRecord):
        raise ValueError("request requires explicit provider consent.")
    if not isinstance(request.secret_ref, ProviderSecretRef):
        raise ValueError("request secret_ref must be ProviderSecretRef.")
    if not _profile_matches_selection(profile, request.selection):
        raise ValueError("profile must match provider selection.")
    if not _selections_match(request.selection, request.consent.selection):
        raise ValueError("consent must match provider selection.")
    if request.secret_ref.profile_id != request.selection.profile_id:
        raise ValueError("secret_ref must match provider selection.")
    if not (
        profile.sends_user_content is True
        and profile.requires_explicit_consent is True
        and request.selection.sends_user_content is True
        and request.selection.requires_explicit_consent is True
        and request.consent.sends_user_content is True
        and request.consent.requires_explicit_consent is True
        and request.consent.has_explicit_consent is True
    ):
        raise ValueError("explicit consent is required for provider dry run.")


def _build_preview_source_chunk(
    execution_input: ProviderDryRunExecutionInput,
) -> SourceChunk:
    preview = execution_input.extraction_text
    preview_hash = hashlib.sha256(preview.encode("utf-8")).hexdigest()
    return SourceChunk(
        chunk_id=execution_input.request.source_chunk_id,
        document_id="provider_dry_run_preview",
        file_path="",
        file_name="provider_dry_run_preview",
        heading_path=["Provider dry run preview"],
        heading_level=1,
        ordinal=0,
        text=preview,
        chunk_hash=preview_hash,
        source_display="Provider dry run preview",
    )


def _normalize_extraction_outcome(
    outcome: KnowledgePointExtractionOutcome,
) -> ProviderDryRunExecutorOutcome:
    if not isinstance(outcome, KnowledgePointExtractionOutcome):
        raise ValueError(
            "extractor must return KnowledgePointExtractionOutcome."
        )
    if outcome.succeeded:
        return ProviderDryRunExecutorOutcome(
            knowledge_points=tuple(outcome.knowledge_points)
        )
    return ProviderDryRunExecutorOutcome(
        error_kind=_map_structured_error_kind(outcome)
    )


def _map_structured_error_kind(
    outcome: KnowledgePointExtractionOutcome,
) -> ProviderErrorKind:
    if outcome.error is None:
        return ProviderErrorKind.UNKNOWN_ERROR
    normalized_values = {outcome.error.code, outcome.error.error_type}
    if "invalid_json" in normalized_values:
        return ProviderErrorKind.INVALID_JSON
    if "malformed_response" in normalized_values:
        return ProviderErrorKind.MALFORMED_RESPONSE
    return ProviderErrorKind.UNKNOWN_ERROR


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
