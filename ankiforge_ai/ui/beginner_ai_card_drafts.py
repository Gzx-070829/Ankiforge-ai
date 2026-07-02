"""Explicit-click AI card drafts for the disposable beginner walkthrough."""

from dataclasses import dataclass, field
from enum import Enum
import json
import socket
from typing import Optional
import urllib.error
from urllib.parse import urlsplit

from ..pipeline.openai_compatible_http_transport import (
    OpenAICompatibleHTTPTransport,
)
from ..pipeline.openai_compatible_provider import (
    OpenAICompatibleTransport,
    build_chat_completions_url,
)
from .beginner_flow_models import (
    BeginnerAICardDraft,
    BeginnerAIGenerationState,
)


BEGINNER_AI_PROVIDER_DISCLOSURE_COPY = (
    "只有点击“用 AI 生成候选卡”后，当前材料才会发送给所选 AI Provider。"
    "本次请求会联网；API key 只用于当前窗口，不会保存；当前不会写入 Anki。"
)

BEGINNER_AI_PROVIDER_ERROR_COPY = (
    "AI 生成失败。你可以检查 API key、模型名称、base_url 或稍后重试。"
    "没有写入 Anki，也没有访问 Anki collection。"
)

BEGINNER_AI_TIMEOUT_COPY = (
    "AI 响应超时。没有写入 Anki，你可以重试。"
    "没有访问 Anki collection。"
)

BEGINNER_AI_INVALID_JSON_COPY = (
    "AI 返回的格式暂时无法解析。没有写入 Anki，你可以重新生成。"
    "没有访问 Anki collection。"
)

BEGINNER_AI_EMPTY_OUTPUT_COPY = (
    "AI 没有返回可解析的内容。没有写入 Anki，你可以重新生成。"
    "没有访问 Anki collection。"
)

BEGINNER_AI_EMPTY_CARDS_COPY = (
    "这次没有生成可用候选卡。可以换一段更完整的材料，或重新生成。"
    "没有写入 Anki，也没有访问 Anki collection。"
)

BEGINNER_AI_SAFE_ERROR_COPY = BEGINNER_AI_PROVIDER_ERROR_COPY

BEGINNER_AI_SETTINGS_HELP_COPY = (
    "请填写本次会话的 Provider、Base URL、模型和 API key，"
    "并确认你了解本次联网发送。当前不会写入 Anki。"
)

BEGINNER_AI_GENERATING_COPY = (
    "生成中：正在向所选 AI Provider 发送当前材料，请稍候。"
    "当前不会写入 Anki，也不会访问 Anki collection。"
)


_SYSTEM_PROMPT = (
    "You create concise question-and-answer drafts for Anki review. "
    "Return JSON only, with no markdown fences or commentary. "
    "Use only facts present in the user's material and do not invent facts."
)

_USER_PROMPT_TEMPLATE = """Create at most {max_cards} Basic Anki card drafts.
Front must be a short, clear question. Back must be accurate and useful for review.
Include a short source_excerpt copied or closely quoted from the supplied material.
If the material is insufficient, return fewer cards or an empty cards array.
Return a JSON array in this exact shape:
[{{"front":"...","back":"...","source_excerpt":"..."}}]

Learning material:
{material_text}"""


class BeginnerAIDraftErrorCode(str, Enum):
    REQUEST_FAILED = "request_failed"
    TIMEOUT = "timeout"
    MALFORMED_RESPONSE = "malformed_response"
    INVALID_CARD_PAYLOAD = "invalid_card_payload"
    EMPTY_OUTPUT = "empty_output"
    NO_CARDS = "no_cards"


@dataclass(frozen=True)
class BeginnerAIProviderRuntimeSettings:
    """One-call settings whose secret is excluded from every safe display."""

    provider_name: str
    base_url: str
    model: str
    api_key: str = field(repr=False)
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        for value, name in (
            (self.provider_name, "provider_name"),
            (self.base_url, "base_url"),
            (self.model, "model"),
            (self.api_key, "api_key"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        parsed_url = urlsplit(self.base_url.strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("base_url must be an HTTP or HTTPS URL.")
        if (
            parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError("base_url must not contain credentials or query data.")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive.")

    def to_safe_dict(self) -> dict:
        return {
            "provider_name": self.provider_name,
            "base_url": self.base_url,
            "model": self.model,
            "credential_supplied": bool(self.api_key),
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class BeginnerAICardDraftGenerationResult:
    """Safe result without raw response, exception, material, or credentials."""

    state: BeginnerAIGenerationState = BeginnerAIGenerationState.IDLE
    drafts: tuple[BeginnerAICardDraft, ...] = field(
        default_factory=tuple,
        repr=False,
    )
    error_code: Optional[BeginnerAIDraftErrorCode] = None
    user_message: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.state, BeginnerAIGenerationState):
            raise ValueError("state must be a BeginnerAIGenerationState.")
        if not isinstance(self.drafts, tuple) or not all(
            isinstance(item, BeginnerAICardDraft) for item in self.drafts
        ):
            raise ValueError("drafts must contain only BeginnerAICardDraft values.")
        if self.error_code is not None and not isinstance(
            self.error_code,
            BeginnerAIDraftErrorCode,
        ):
            raise ValueError("error_code must be a BeginnerAIDraftErrorCode.")
        if self.error_code is not None and self.drafts:
            raise ValueError("failed results cannot contain drafts.")
        if self.state is BeginnerAIGenerationState.SUCCESS and not self.drafts:
            raise ValueError("successful results must contain drafts.")
        if self.state is not BeginnerAIGenerationState.SUCCESS and self.drafts:
            raise ValueError("only successful results can contain drafts.")
        if not isinstance(self.user_message, str):
            raise ValueError("user_message must be a string.")

    @property
    def success(self) -> bool:
        return (
            self.state is BeginnerAIGenerationState.SUCCESS
            and bool(self.drafts)
            and self.error_code is None
        )

    def to_safe_dict(self) -> dict:
        return {
            "success": self.success,
            "state": self.state.value,
            "draft_count": len(self.drafts),
            "error_code": self.error_code.value if self.error_code else None,
            "user_message": self.user_message,
        }


class BeginnerAICardDraftGenerator:
    """Call an OpenAI-compatible endpoint only when generate() is invoked."""

    def __init__(
        self,
        transport: Optional[OpenAICompatibleTransport] = None,
    ):
        self._transport = transport

    def generate(
        self,
        settings: BeginnerAIProviderRuntimeSettings,
        material_text: str,
        max_cards: int = 5,
    ) -> BeginnerAICardDraftGenerationResult:
        if not isinstance(settings, BeginnerAIProviderRuntimeSettings):
            raise ValueError("settings must be BeginnerAIProviderRuntimeSettings.")
        if not isinstance(material_text, str) or not material_text.strip():
            return _failure(BeginnerAIGenerationState.EMPTY_CARDS)
        if (
            isinstance(max_cards, bool)
            or not isinstance(max_cards, int)
            or not 1 <= max_cards <= 5
        ):
            raise ValueError("max_cards must be an integer from 1 to 5.")

        transport = self._transport or OpenAICompatibleHTTPTransport()
        try:
            response = transport.post_json(
                url=build_chat_completions_url(settings.base_url),
                headers={
                    "Authorization": f"Bearer {settings.api_key}",
                    "Content-Type": "application/json",
                },
                payload=_build_payload(settings, material_text, max_cards),
                timeout_seconds=settings.timeout_seconds,
            )
        except Exception as error:
            state = (
                BeginnerAIGenerationState.TIMEOUT
                if _is_timeout_error(error)
                else BeginnerAIGenerationState.PROVIDER_ERROR
            )
            return _failure(state)

        status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int) or not 200 <= status_code < 300:
            return _failure(BeginnerAIGenerationState.PROVIDER_ERROR)
        content = _extract_assistant_content(response.json_body)
        if not content:
            return _failure(BeginnerAIGenerationState.EMPTY_OUTPUT)
        return parse_beginner_ai_card_drafts(content, max_cards=max_cards)


def parse_beginner_ai_card_drafts(
    json_text: str,
    max_cards: int = 5,
) -> BeginnerAICardDraftGenerationResult:
    """Parse a JSON array or {cards: [...]} into isolated draft models."""

    if not isinstance(json_text, str) or not json_text.strip():
        return _failure(BeginnerAIGenerationState.EMPTY_OUTPUT)
    if (
        isinstance(max_cards, bool)
        or not isinstance(max_cards, int)
        or not 1 <= max_cards <= 5
    ):
        raise ValueError("max_cards must be an integer from 1 to 5.")
    payload = _extract_first_json_value(_strip_markdown_fence(json_text.strip()))
    if payload is None:
        return _failure(BeginnerAIGenerationState.INVALID_JSON)

    cards = payload.get("cards") if isinstance(payload, dict) else payload
    if not isinstance(cards, list):
        return _failure(BeginnerAIGenerationState.INVALID_JSON)
    if not cards:
        return _failure(BeginnerAIGenerationState.EMPTY_CARDS)

    drafts = []
    for index, card in enumerate(cards[:max_cards], start=1):
        if not isinstance(card, dict):
            return _failure(BeginnerAIGenerationState.INVALID_JSON)
        front = _validated_text(card.get("front"), max_chars=500)
        back = _validated_text(card.get("back"), max_chars=4000)
        source_excerpt = _validated_text(
            card.get("source_excerpt") or card.get("rationale"),
            max_chars=1000,
        )
        if not all((front, back, source_excerpt)):
            return _failure(BeginnerAIGenerationState.INVALID_JSON)
        drafts.append(
            BeginnerAICardDraft(
                id=f"ai-draft-{index}",
                front=front,
                back=back,
                source_excerpt=source_excerpt,
            )
        )

    return BeginnerAICardDraftGenerationResult(
        state=BeginnerAIGenerationState.SUCCESS,
        drafts=tuple(drafts),
        user_message=(
            f"已生成 {len(drafts)} 张只读候选卡草稿，请逐张核对。"
            "当前不会写入 Anki。"
        ),
    )


def _build_payload(
    settings: BeginnerAIProviderRuntimeSettings,
    material_text: str,
    max_cards: int,
) -> dict:
    return {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _USER_PROMPT_TEMPLATE.format(
                    max_cards=max_cards,
                    material_text=material_text,
                ),
            },
        ],
        "temperature": 0.2,
    }


def _extract_assistant_content(json_body: object) -> Optional[str]:
    try:
        content = json_body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()


def _strip_markdown_fence(text: str) -> str:
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def _extract_first_json_value(text: str) -> object:
    decoder = json.JSONDecoder()
    try:
        value, _ = decoder.raw_decode(text)
        if isinstance(value, (list, dict)):
            return value
    except json.JSONDecodeError:
        pass

    for index, character in enumerate(text):
        if character not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, (list, dict)):
            return value
    return None


def _validated_text(value: object, max_chars: int) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if not normalized or len(normalized) > max_chars:
        return ""
    return normalized


def _is_timeout_error(error: Exception) -> bool:
    if isinstance(error, (TimeoutError, socket.timeout)):
        return True
    if isinstance(error, urllib.error.URLError):
        return isinstance(error.reason, (TimeoutError, socket.timeout))
    return False


_ERROR_DETAILS = {
    BeginnerAIGenerationState.PROVIDER_ERROR: (
        BeginnerAIDraftErrorCode.REQUEST_FAILED,
        BEGINNER_AI_PROVIDER_ERROR_COPY,
    ),
    BeginnerAIGenerationState.TIMEOUT: (
        BeginnerAIDraftErrorCode.TIMEOUT,
        BEGINNER_AI_TIMEOUT_COPY,
    ),
    BeginnerAIGenerationState.INVALID_JSON: (
        BeginnerAIDraftErrorCode.MALFORMED_RESPONSE,
        BEGINNER_AI_INVALID_JSON_COPY,
    ),
    BeginnerAIGenerationState.EMPTY_OUTPUT: (
        BeginnerAIDraftErrorCode.EMPTY_OUTPUT,
        BEGINNER_AI_EMPTY_OUTPUT_COPY,
    ),
    BeginnerAIGenerationState.EMPTY_CARDS: (
        BeginnerAIDraftErrorCode.NO_CARDS,
        BEGINNER_AI_EMPTY_CARDS_COPY,
    ),
}


def _failure(
    state: BeginnerAIGenerationState,
) -> BeginnerAICardDraftGenerationResult:
    code, user_message = _ERROR_DETAILS[state]
    return BeginnerAICardDraftGenerationResult(
        state=state,
        error_code=code,
        user_message=user_message,
    )
