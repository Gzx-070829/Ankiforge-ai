"""Pure provider contracts for knowledge-point JSON extraction."""

from dataclasses import dataclass
from typing import Optional, Protocol, Tuple, runtime_checkable

from .models import SourceChunk


@dataclass(frozen=True)
class AIProviderMetadata:
    provider_id: str
    model: str

    def __post_init__(self) -> None:
        _require_text(self.provider_id, "provider_id")
        _require_text(self.model, "model")

    def to_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "model": self.model,
        }


@dataclass(frozen=True)
class KnowledgePointExtractionRequest:
    request_id: str
    document_id: str
    chunk_id: str
    source_display: str
    heading_path: Tuple[str, ...]
    text: str

    def __post_init__(self) -> None:
        _require_text(self.request_id, "request_id")
        _require_text(self.document_id, "document_id")
        _require_text(self.chunk_id, "chunk_id")
        if not isinstance(self.source_display, str):
            raise ValueError("source_display must be a string.")
        if not isinstance(self.text, str):
            raise ValueError("text must be a string.")
        object.__setattr__(self, "heading_path", tuple(self.heading_path))

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "source_display": self.source_display,
            "heading_path": list(self.heading_path),
            "text": self.text,
        }


@dataclass(frozen=True)
class KnowledgePointExtractionResponse:
    request_id: str
    chunk_id: str
    metadata: AIProviderMetadata
    json_text: str

    def __post_init__(self) -> None:
        _require_text(self.request_id, "request_id")
        _require_text(self.chunk_id, "chunk_id")
        if not isinstance(self.metadata, AIProviderMetadata):
            raise ValueError("metadata must be AIProviderMetadata.")
        if not isinstance(self.json_text, str):
            raise ValueError("json_text must be a string.")

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "chunk_id": self.chunk_id,
            "metadata": self.metadata.to_dict(),
            "json_text": self.json_text,
        }


@dataclass(frozen=True)
class AIProviderError:
    code: str
    message: str
    error_type: str = ""
    retryable: bool = False

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        _require_text(self.message, "message")
        if not isinstance(self.error_type, str):
            raise ValueError("error_type must be a string.")
        if not isinstance(self.retryable, bool):
            raise ValueError("retryable must be a bool.")

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "error_type": self.error_type,
            "retryable": self.retryable,
        }


@dataclass(frozen=True)
class AIProviderResult:
    request_id: str
    chunk_id: str
    response: Optional[KnowledgePointExtractionResponse] = None
    error: Optional[AIProviderError] = None

    def __post_init__(self) -> None:
        _require_text(self.request_id, "request_id")
        _require_text(self.chunk_id, "chunk_id")
        if (self.response is None) == (self.error is None):
            raise ValueError("Provider result must contain exactly one response or error.")
        if self.response is not None and not isinstance(
            self.response,
            KnowledgePointExtractionResponse,
        ):
            raise ValueError("response must be KnowledgePointExtractionResponse.")
        if self.error is not None and not isinstance(self.error, AIProviderError):
            raise ValueError("error must be AIProviderError.")
        if self.response is not None and (
            self.request_id != self.response.request_id
            or self.chunk_id != self.response.chunk_id
        ):
            raise ValueError("Provider result and response IDs must match.")

    @property
    def success(self) -> bool:
        return self.response is not None

    @classmethod
    def from_response(
        cls,
        response: KnowledgePointExtractionResponse,
    ) -> "AIProviderResult":
        return cls(
            request_id=response.request_id,
            chunk_id=response.chunk_id,
            response=response,
        )

    @classmethod
    def from_error(
        cls,
        request: KnowledgePointExtractionRequest,
        error: AIProviderError,
    ) -> "AIProviderResult":
        return cls(
            request_id=request.request_id,
            chunk_id=request.chunk_id,
            error=error,
        )

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "chunk_id": self.chunk_id,
            "success": self.success,
            "response": self.response.to_dict() if self.response else None,
            "error": self.error.to_dict() if self.error else None,
        }


@runtime_checkable
class KnowledgePointJSONProvider(Protocol):
    metadata: AIProviderMetadata

    def extract(
        self,
        request: KnowledgePointExtractionRequest,
    ) -> AIProviderResult:
        """Return knowledge-point JSON or a structured provider error."""


def build_knowledge_point_extraction_request(
    chunk: SourceChunk,
    request_id: str = "",
) -> KnowledgePointExtractionRequest:
    return KnowledgePointExtractionRequest(
        request_id=request_id or f"kp_extract_{chunk.chunk_id}",
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        source_display=chunk.source_display,
        heading_path=tuple(chunk.heading_path),
        text=str(chunk.text or ""),
    )


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
