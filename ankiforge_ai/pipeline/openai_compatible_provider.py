"""Transport-injected OpenAI-compatible provider for knowledge point JSON."""

from dataclasses import dataclass, field
from typing import Mapping, Optional, Protocol, runtime_checkable

from .http_error_sanitization import sanitize_provider_error_detail

from .ai_provider_contracts import (
    AIProviderError,
    AIProviderMetadata,
    AIProviderResult,
    KnowledgePointExtractionRequest,
    KnowledgePointExtractionResponse,
)


_JSON_ONLY_INSTRUCTION = (
    'Return JSON only in this shape: {"knowledge_points": [...]}. '
    "Each knowledge point must include a non-empty title and explanation."
)


@dataclass(frozen=True)
class OpenAICompatibleProviderConfig:
    provider_id: str
    provider_name: str
    model_name: str
    base_url: str
    api_key: str = field(repr=False)
    privacy_notice: str = ""
    timeout_seconds: Optional[float] = 60.0

    def __post_init__(self) -> None:
        _require_text(self.provider_id, "provider_id")
        _require_text(self.provider_name, "provider_name")
        _require_text(self.model_name, "model_name")
        _require_text(self.base_url, "base_url")
        _require_text(self.api_key, "api_key")
        if not isinstance(self.privacy_notice, str):
            raise ValueError("privacy_notice must be a string.")
        if self.timeout_seconds is not None and (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive or None.")

    def to_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "privacy_notice": self.privacy_notice,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class OpenAICompatibleTransportResponse:
    status_code: int
    json_body: object = field(repr=False)
    error_detail: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.status_code, bool) or not isinstance(self.status_code, int):
            raise ValueError("status_code must be an integer.")
        if not isinstance(self.error_detail, str):
            raise ValueError("error_detail must be a string.")
        object.__setattr__(
            self,
            "error_detail",
            sanitize_provider_error_detail(self.error_detail),
        )


@runtime_checkable
class OpenAICompatibleTransport(Protocol):
    def post_json(
        self,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: Optional[float],
    ) -> OpenAICompatibleTransportResponse:
        """Return a decoded response without prescribing an HTTP client."""


class OpenAICompatibleKnowledgePointProvider:
    """Build chat-completion requests through an injected transport."""

    def __init__(
        self,
        config: OpenAICompatibleProviderConfig,
        transport: OpenAICompatibleTransport,
    ):
        self._config = config
        self._transport = transport
        self.metadata = AIProviderMetadata(
            provider_id=config.provider_id,
            model=config.model_name,
        )

    def extract(
        self,
        request: KnowledgePointExtractionRequest,
    ) -> AIProviderResult:
        response = self._transport.post_json(
            url=build_chat_completions_url(self._config.base_url),
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            payload=build_chat_completions_payload(request, self._config),
            timeout_seconds=self._config.timeout_seconds,
        )

        if not 200 <= response.status_code < 300:
            return AIProviderResult.from_error(
                request,
                AIProviderError(
                    code="http_error",
                    message=(
                        f"Provider '{self.metadata.provider_id}' returned "
                        f"HTTP {response.status_code}."
                    ),
                    error_type="http_error",
                    retryable=False,
                ),
            )

        content = _extract_assistant_content(response.json_body)
        if content is None:
            return AIProviderResult.from_error(
                request,
                AIProviderError(
                    code="malformed_response",
                    message=(
                        f"Provider '{self.metadata.provider_id}' returned "
                        "a malformed response."
                    ),
                    error_type="malformed_response",
                    retryable=False,
                ),
            )

        return AIProviderResult.from_response(
            KnowledgePointExtractionResponse(
                request_id=request.request_id,
                chunk_id=request.chunk_id,
                metadata=self.metadata,
                json_text=content,
            )
        )


def build_chat_completions_url(base_url: str) -> str:
    base = str(base_url or "").strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def build_chat_completions_payload(
    request: KnowledgePointExtractionRequest,
    config: OpenAICompatibleProviderConfig,
) -> dict:
    return {
        "model": config.model_name,
        "messages": [
            {"role": "system", "content": _JSON_ONLY_INSTRUCTION},
            {"role": "user", "content": request.text},
        ],
        "response_format": {"type": "json_object"},
    }


def _extract_assistant_content(json_body: object) -> Optional[str]:
    try:
        content = json_body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
