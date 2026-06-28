"""Safe user-facing display mapping for normalized provider error kinds."""

from dataclasses import dataclass
from enum import Enum


_MAX_PROVIDER_NAME_CHARS = 80
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
    "source text",
    "chunk text",
    "raw payload",
    "raw response",
    "stack trace",
)


class ProviderErrorKind(str, Enum):
    AUTH_ERROR = "auth_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_REQUEST = "invalid_request"
    INVALID_JSON = "invalid_json"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CONTENT_POLICY = "content_policy"
    UNKNOWN_ERROR = "unknown_error"


_ERROR_TEMPLATES = {
    ProviderErrorKind.AUTH_ERROR: (
        "认证失败",
        "AI provider 无法完成认证。",
        "请检查认证设置后再试。",
        False,
    ),
    ProviderErrorKind.NETWORK_ERROR: (
        "网络连接失败",
        "当前无法连接到 AI provider。",
        "请检查网络连接并稍后重试。",
        True,
    ),
    ProviderErrorKind.TIMEOUT: (
        "请求超时",
        "AI provider 未在预期时间内响应。",
        "请稍后重试。",
        True,
    ),
    ProviderErrorKind.RATE_LIMIT: (
        "请求频率受限",
        "AI provider 暂时限制了请求频率。",
        "请稍后重试。",
        True,
    ),
    ProviderErrorKind.QUOTA_EXCEEDED: (
        "可用额度受限",
        "AI provider 未能接受当前请求，可能与可用额度有关。",
        "请检查 provider 账户状态后再试。",
        False,
    ),
    ProviderErrorKind.INVALID_REQUEST: (
        "请求无法处理",
        "AI provider 无法处理当前请求格式。",
        "请检查 provider 与模型设置。",
        False,
    ),
    ProviderErrorKind.INVALID_JSON: (
        "返回格式无效",
        "AI provider 未返回有效的知识点 JSON。",
        "请检查模型是否支持结构化输出。",
        False,
    ),
    ProviderErrorKind.MALFORMED_RESPONSE: (
        "响应格式异常",
        "AI provider 的响应无法安全读取。",
        "请检查 provider 兼容性后再试。",
        False,
    ),
    ProviderErrorKind.PROVIDER_UNAVAILABLE: (
        "服务暂不可用",
        "AI provider 当前无法提供服务。",
        "请稍后重试。",
        True,
    ),
    ProviderErrorKind.CONTENT_POLICY: (
        "内容未被接受",
        "AI provider 未接受本次请求。",
        "请检查 provider 使用规则并调整输入。",
        False,
    ),
    ProviderErrorKind.UNKNOWN_ERROR: (
        "AI provider 出现问题",
        "AI provider 未能完成本次请求。",
        "请检查设置或稍后再试。",
        False,
    ),
}


@dataclass(frozen=True)
class ProviderErrorDisplay:
    """Validated display-only provider error information."""

    kind: ProviderErrorKind
    user_title: str
    user_message: str
    suggested_action: str
    retryable: bool
    safe_diagnostic_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ProviderErrorKind):
            raise ValueError("kind must be ProviderErrorKind.")
        for field_name in (
            "user_title",
            "user_message",
            "suggested_action",
            "safe_diagnostic_code",
        ):
            _require_safe_text(getattr(self, field_name), field_name)
        if type(self.retryable) is not bool:
            raise ValueError("retryable must be a bool.")

    def to_safe_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "user_title": self.user_title,
            "user_message": self.user_message,
            "suggested_action": self.suggested_action,
            "retryable": self.retryable,
            "safe_diagnostic_code": self.safe_diagnostic_code,
        }


def create_provider_error_display(
    kind: ProviderErrorKind,
    provider_name: str | None = None,
) -> ProviderErrorDisplay:
    """Map one normalized kind to fixed, credential-free display text."""
    if not isinstance(kind, ProviderErrorKind):
        raise ValueError("kind must be ProviderErrorKind.")
    safe_provider_name = _normalize_provider_name(provider_name)
    title, message, action, retryable = _ERROR_TEMPLATES[kind]
    provider_label = safe_provider_name or "AI provider"
    return ProviderErrorDisplay(
        kind=kind,
        user_title=f"{provider_label}：{title}",
        user_message=message,
        suggested_action=action,
        retryable=retryable,
        safe_diagnostic_code=f"provider_error.{kind.value}",
    )


def _normalize_provider_name(provider_name: str | None) -> str | None:
    if provider_name is None:
        return None
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise ValueError("provider_name must be a non-empty safe display string.")
    normalized = provider_name.strip()
    if len(normalized) > _MAX_PROVIDER_NAME_CHARS:
        raise ValueError("provider_name must not exceed 80 characters.")
    _require_safe_text(normalized, "provider_name")
    return normalized


def _require_safe_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field_name} must not contain control characters.")
    lowered = value.lower()
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        raise ValueError(f"{field_name} contains unsafe display content.")
