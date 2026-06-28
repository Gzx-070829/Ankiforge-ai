"""Safe, read-only diagnostics for an AI knowledge-point dry run."""

from dataclasses import dataclass
from typing import Optional

from .ai_extraction_service import KnowledgePointExtractionOutcome
from .ai_provider_contracts import AIProviderError


_USER_SAFE_ERROR_MESSAGES = {
    "invalid_json": "AI 返回的 JSON 格式无效，需要重新生成或调整 provider 输出。",
    "malformed_response": "AI provider 返回格式异常，未能读取有效内容。",
    "provider_exception": "AI provider 调用失败，已被安全拦截。",
    "network_error": "网络请求失败。",
    "auth_error": "API key 或认证配置可能有问题。",
    "rate_limit": "请求频率受限，请稍后重试。",
    "http_error": "AI provider 请求失败。",
}
_UNKNOWN_ERROR_MESSAGE = "AI provider 出现未知错误。"
_SUCCESS_MESSAGE = "AI 知识点提取完成。"


@dataclass(frozen=True)
class ProviderDryRunContext:
    """Explicit provider display data without credentials or source content."""

    provider_id: str
    provider_name: str
    model_name: str
    is_mock: bool
    sends_user_content: bool
    supports_json_output: bool
    safety_wrapped: bool

    def __post_init__(self) -> None:
        _require_text(self.provider_id, "provider_id")
        _require_text(self.provider_name, "provider_name")
        _require_text(self.model_name, "model_name")
        for field_name in (
            "is_mock",
            "sends_user_content",
            "supports_json_output",
            "safety_wrapped",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a bool.")

    def to_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "is_mock": self.is_mock,
            "sends_user_content": self.sends_user_content,
            "supports_json_output": self.supports_json_output,
            "safety_wrapped": self.safety_wrapped,
        }


@dataclass(frozen=True)
class ProviderDryRunSummary:
    """Credential-free diagnostics; this object never authorizes an Anki write."""

    provider_id: str
    provider_name: str
    model_name: str
    is_mock: bool
    sends_user_content: bool
    supports_json_output: bool
    safety_wrapped: bool
    succeeded: bool
    knowledge_point_count: int
    error_type: str
    error_code: str
    retryable: bool
    user_safe_message: str

    @property
    def will_write_to_anki(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "is_mock": self.is_mock,
            "sends_user_content": self.sends_user_content,
            "supports_json_output": self.supports_json_output,
            "safety_wrapped": self.safety_wrapped,
            "succeeded": self.succeeded,
            "knowledge_point_count": self.knowledge_point_count,
            "error_type": self.error_type,
            "error_code": self.error_code,
            "retryable": self.retryable,
            "user_safe_message": self.user_safe_message,
            "will_write_to_anki": self.will_write_to_anki,
        }


def create_provider_dry_run_summary(
    outcome: KnowledgePointExtractionOutcome,
    context: ProviderDryRunContext,
) -> ProviderDryRunSummary:
    """Summarize an existing extraction outcome without invoking its provider."""
    if not isinstance(outcome, KnowledgePointExtractionOutcome):
        raise ValueError("outcome must be KnowledgePointExtractionOutcome.")
    if not isinstance(context, ProviderDryRunContext):
        raise ValueError("context must be ProviderDryRunContext.")

    error = outcome.error
    return ProviderDryRunSummary(
        provider_id=context.provider_id,
        provider_name=context.provider_name,
        model_name=context.model_name,
        is_mock=context.is_mock,
        sends_user_content=context.sends_user_content,
        supports_json_output=context.supports_json_output,
        safety_wrapped=context.safety_wrapped,
        succeeded=outcome.succeeded,
        knowledge_point_count=(
            len(outcome.knowledge_points) if outcome.succeeded else 0
        ),
        error_type=error.error_type if error else "",
        error_code=error.code if error else "",
        retryable=error.retryable if error else False,
        user_safe_message=(
            _build_user_safe_error_message(error) if error else _SUCCESS_MESSAGE
        ),
    )


def _build_user_safe_error_message(error: AIProviderError) -> str:
    error_type = error.error_type.strip().lower()
    error_code = error.code.strip().lower()
    if error_type in _USER_SAFE_ERROR_MESSAGES:
        return _USER_SAFE_ERROR_MESSAGES[error_type]
    if error_code in _USER_SAFE_ERROR_MESSAGES:
        return _USER_SAFE_ERROR_MESSAGES[error_code]
    return _UNKNOWN_ERROR_MESSAGE


def _require_text(value: Optional[str], field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
