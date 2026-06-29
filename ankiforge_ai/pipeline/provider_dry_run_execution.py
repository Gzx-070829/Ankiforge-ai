"""Consent-gated, fake-only execution boundary for provider dry runs."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .models import KnowledgePoint
from .provider_consent import ProviderConsentRecord, ProviderSelection
from .provider_dry_run_request import ProviderDryRunRequest
from .provider_error_display import (
    ProviderErrorDisplay,
    ProviderErrorKind,
    create_provider_error_display,
)
from .provider_secret_store import ProviderSecretRef


_TARGET_STAGE = "knowledge_point_extraction"
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
    "stack trace",
)


@dataclass(frozen=True)
class ProviderDryRunExecutionInput:
    """Validated request carrier whose execution text is the existing preview."""

    request: ProviderDryRunRequest = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.request, ProviderDryRunRequest):
            raise ValueError("request must be ProviderDryRunRequest.")
        if not isinstance(self.request.selection, ProviderSelection):
            raise ValueError("request selection must be ProviderSelection.")
        _require_safe_identifier(
            self.request.selection.profile_id,
            "profile_id",
        )
        _require_safe_identifier(
            self.request.source_chunk_id,
            "source_chunk_id",
        )

    @property
    def extraction_text(self) -> str:
        return self.request.source_excerpt_preview

    @property
    def target_stage(self) -> str | None:
        return _request_target_stage(self.request)

    def to_safe_dict(self) -> dict:
        return {
            "profile_id": self.request.selection.profile_id,
            "source_chunk_id": self.request.source_chunk_id,
            "source_excerpt_preview_length": len(
                self.request.source_excerpt_preview
            ),
            "target_stage": self.target_stage,
        }


@dataclass(frozen=True)
class ProviderDryRunExecutorOutcome:
    """Normalized fake-executor outcome without raw provider diagnostics."""

    knowledge_points: tuple[KnowledgePoint, ...] = field(
        default_factory=tuple,
        repr=False,
    )
    error_kind: ProviderErrorKind | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.knowledge_points, tuple):
            raise ValueError("knowledge_points must be a tuple.")
        if not all(
            isinstance(point, KnowledgePoint) for point in self.knowledge_points
        ):
            raise ValueError(
                "knowledge_points must contain only KnowledgePoint values."
            )
        if self.error_kind is not None and not isinstance(
            self.error_kind,
            ProviderErrorKind,
        ):
            raise ValueError("error_kind must be ProviderErrorKind or None.")
        if self.error_kind is not None and self.knowledge_points:
            raise ValueError(
                "failed executor outcomes cannot contain knowledge points."
            )

    @property
    def success(self) -> bool:
        return self.error_kind is None


@runtime_checkable
class ProviderDryRunExecutor(Protocol):
    """Structural contract for an explicitly supplied dry-run executor."""

    def execute(
        self,
        execution_input: ProviderDryRunExecutionInput,
    ) -> ProviderDryRunExecutorOutcome:
        ...


@dataclass(frozen=True)
class ProviderDryRunExecutionResult:
    """Safe execution result that stops at knowledge-point extraction."""

    profile_id: str
    source_chunk_id: str
    source_excerpt_preview_length: int
    knowledge_points: tuple[KnowledgePoint, ...] = field(repr=False)
    error_display: ProviderErrorDisplay | None = None

    def __post_init__(self) -> None:
        _require_safe_identifier(self.profile_id, "profile_id")
        _require_safe_identifier(self.source_chunk_id, "source_chunk_id")
        if (
            isinstance(self.source_excerpt_preview_length, bool)
            or not isinstance(self.source_excerpt_preview_length, int)
            or self.source_excerpt_preview_length < 1
        ):
            raise ValueError(
                "source_excerpt_preview_length must be a positive integer."
            )
        if not isinstance(self.knowledge_points, tuple):
            raise ValueError("knowledge_points must be a tuple.")
        if not all(
            isinstance(point, KnowledgePoint) for point in self.knowledge_points
        ):
            raise ValueError(
                "knowledge_points must contain only KnowledgePoint values."
            )
        if self.error_display is not None and not isinstance(
            self.error_display,
            ProviderErrorDisplay,
        ):
            raise ValueError(
                "error_display must be ProviderErrorDisplay or None."
            )
        if self.error_display is not None and self.knowledge_points:
            raise ValueError(
                "failed execution results cannot contain knowledge points."
            )

    @property
    def success(self) -> bool:
        return self.error_display is None

    @property
    def target_stage(self) -> str:
        return _TARGET_STAGE

    @property
    def will_write_to_anki(self) -> bool:
        return False

    @property
    def will_generate_cards(self) -> bool:
        return False

    @property
    def will_create_anki_notes(self) -> bool:
        return False

    @property
    def will_modify_self_cards(self) -> bool:
        return False

    def to_safe_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "source_chunk_id": self.source_chunk_id,
            "source_excerpt_preview_length": self.source_excerpt_preview_length,
            "success": self.success,
            "knowledge_point_count": len(self.knowledge_points),
            "error_display": (
                self.error_display.to_safe_dict()
                if self.error_display is not None
                else None
            ),
            "target_stage": self.target_stage,
            "will_write_to_anki": self.will_write_to_anki,
            "will_generate_cards": self.will_generate_cards,
            "will_create_anki_notes": self.will_create_anki_notes,
            "will_modify_self_cards": self.will_modify_self_cards,
        }


def execute_provider_dry_run_with_boundary(
    execution_input: ProviderDryRunExecutionInput,
    executor: ProviderDryRunExecutor,
) -> ProviderDryRunExecutionResult:
    """Run one explicit executor after revalidating all consent boundaries."""
    if not isinstance(execution_input, ProviderDryRunExecutionInput):
        raise ValueError(
            "execution_input must be ProviderDryRunExecutionInput."
        )
    if executor is None or not isinstance(executor, ProviderDryRunExecutor):
        raise ValueError("executor must implement ProviderDryRunExecutor.")

    request = execution_input.request
    _validate_request_boundary(request)
    outcome = executor.execute(execution_input)
    if not isinstance(outcome, ProviderDryRunExecutorOutcome):
        raise ValueError(
            "executor must return ProviderDryRunExecutorOutcome."
        )

    error_display = (
        create_provider_error_display(
            outcome.error_kind,
            provider_name=request.selection.provider_name,
        )
        if outcome.error_kind is not None
        else None
    )
    return ProviderDryRunExecutionResult(
        profile_id=request.selection.profile_id,
        source_chunk_id=request.source_chunk_id,
        source_excerpt_preview_length=len(request.source_excerpt_preview),
        knowledge_points=tuple(outcome.knowledge_points),
        error_display=error_display,
    )


def _validate_request_boundary(request: ProviderDryRunRequest) -> None:
    if not isinstance(request, ProviderDryRunRequest):
        raise ValueError("request must be ProviderDryRunRequest.")
    if not isinstance(request.selection, ProviderSelection):
        raise ValueError("request selection must be ProviderSelection.")
    if not isinstance(request.consent, ProviderConsentRecord):
        raise ValueError("request requires explicit provider consent.")
    if not isinstance(request.secret_ref, ProviderSecretRef):
        raise ValueError("request secret_ref must be ProviderSecretRef.")
    if _request_target_stage(request) != _TARGET_STAGE:
        raise ValueError("request target stage must be knowledge_point_extraction.")
    if not _selections_match(request.selection, request.consent.selection):
        raise ValueError("request consent must match provider selection.")
    if request.secret_ref.profile_id != request.selection.profile_id:
        raise ValueError("request secret_ref must match provider selection.")
    if not (
        request.selection.sends_user_content is True
        and request.selection.requires_explicit_consent is True
    ):
        raise ValueError("provider selection must require explicit consent.")
    if not (
        request.consent.sends_user_content is True
        and request.consent.requires_explicit_consent is True
        and request.consent.has_explicit_consent is True
    ):
        raise ValueError("request requires explicit affirmative consent.")

    _require_safe_identifier(request.selection.profile_id, "profile_id")
    _require_safe_identifier(request.source_chunk_id, "source_chunk_id")
    if (
        not isinstance(request.source_excerpt_preview, str)
        or not request.source_excerpt_preview.strip()
    ):
        raise ValueError("request source preview must be non-empty.")


def _request_target_stage(request: ProviderDryRunRequest) -> str | None:
    safe_request = request.to_safe_dict()
    if not isinstance(safe_request, dict):
        return None
    return safe_request.get("target_stage")


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


def _require_safe_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field_name} must not contain control characters.")
    lowered = value.lower()
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        raise ValueError(f"{field_name} contains unsafe display content.")
