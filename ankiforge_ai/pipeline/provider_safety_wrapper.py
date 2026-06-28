"""Safety wrapper for knowledge point JSON providers."""

from .ai_provider_contracts import (
    AIProviderError,
    AIProviderMetadata,
    AIProviderResult,
    KnowledgePointExtractionRequest,
    KnowledgePointJSONProvider,
)


class SafeKnowledgePointJSONProvider:
    """Convert unexpected provider exceptions into structured failures."""

    def __init__(self, inner_provider: KnowledgePointJSONProvider):
        self._inner_provider = inner_provider

    @property
    def metadata(self) -> AIProviderMetadata:
        return self._inner_provider.metadata

    def extract(
        self,
        request: KnowledgePointExtractionRequest,
    ) -> AIProviderResult:
        try:
            return self._inner_provider.extract(request)
        except Exception as exc:
            error = AIProviderError(
                code="provider_exception",
                message=_safe_exception_message(self.metadata, request, exc),
                error_type="unknown",
                retryable=False,
            )
            return AIProviderResult.from_error(request, error)


def _safe_exception_message(
    metadata: AIProviderMetadata,
    request: KnowledgePointExtractionRequest,
    exc: Exception,
) -> str:
    return (
        f"Provider '{metadata.provider_id}' raised {type(exc).__name__} "
        f"for request '{request.request_id}' and chunk '{request.chunk_id}'."
    )
