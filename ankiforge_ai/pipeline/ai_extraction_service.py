"""Service layer for parsing provider JSON into knowledge points."""

from dataclasses import dataclass
from typing import Optional, Tuple

from .ai_provider_contracts import (
    AIProviderError,
    AIProviderResult,
    KnowledgePointExtractionRequest,
    KnowledgePointJSONProvider,
    build_knowledge_point_extraction_request,
)
from .knowledge_points import parse_knowledge_points_json
from .models import KnowledgePoint, SourceChunk


@dataclass(frozen=True)
class KnowledgePointExtractionOutcome:
    request: KnowledgePointExtractionRequest
    provider_result: AIProviderResult
    knowledge_points: Tuple[KnowledgePoint, ...] = ()
    error: Optional[AIProviderError] = None

    def __post_init__(self) -> None:
        if not isinstance(self.request, KnowledgePointExtractionRequest):
            raise ValueError("request must be KnowledgePointExtractionRequest.")
        if not isinstance(self.provider_result, AIProviderResult):
            raise ValueError("provider_result must be AIProviderResult.")
        object.__setattr__(self, "knowledge_points", tuple(self.knowledge_points))
        if self.error is not None and not isinstance(self.error, AIProviderError):
            raise ValueError("error must be AIProviderError.")

    @property
    def succeeded(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict:
        return {
            "request": self.request.to_dict(),
            "provider_result": self.provider_result.to_dict(),
            "knowledge_points": [point.to_dict() for point in self.knowledge_points],
            "succeeded": self.succeeded,
            "error": self.error.to_dict() if self.error else None,
        }


def extract_knowledge_points(
    chunk: SourceChunk,
    provider: KnowledgePointJSONProvider,
    request_id: str = "",
) -> KnowledgePointExtractionOutcome:
    request = build_knowledge_point_extraction_request(chunk, request_id=request_id)
    provider_result = provider.extract(request)

    if not provider_result.success:
        return KnowledgePointExtractionOutcome(
            request=request,
            provider_result=provider_result,
            error=provider_result.error,
        )

    try:
        knowledge_points = parse_knowledge_points_json(
            provider_result.response.json_text,
            chunk,
        )
    except ValueError as exc:
        return KnowledgePointExtractionOutcome(
            request=request,
            provider_result=provider_result,
            error=AIProviderError(
                code="invalid_json",
                message=str(exc),
                error_type="invalid_json",
                retryable=False,
            ),
        )

    return KnowledgePointExtractionOutcome(
        request=request,
        provider_result=provider_result,
        knowledge_points=tuple(knowledge_points),
    )


def extract_knowledge_points_from_chunks(
    chunks,
    provider: KnowledgePointJSONProvider,
) -> list[KnowledgePointExtractionOutcome]:
    return [extract_knowledge_points(chunk, provider) for chunk in chunks]
