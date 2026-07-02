"""Explicit-click AI card drafts for the disposable beginner walkthrough."""

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Optional
from urllib.parse import urlsplit

from ..pipeline.openai_compatible_http_transport import (
    OpenAICompatibleHTTPTransport,
)
from ..pipeline.openai_compatible_provider import (
    OpenAICompatibleTransport,
    build_chat_completions_url,
)
from .beginner_flow_models import BeginnerAICardDraft


BEGINNER_AI_PROVIDER_DISCLOSURE_COPY = (
    "只有点击“用 AI 生成候选卡”后，当前材料才会发送给所选 AI Provider。"
    "本次请求会联网；API key 只用于当前窗口，不会保存；当前不会写入 Anki。"
)

BEGINNER_AI_SAFE_ERROR_COPY = (
    "未能生成可审核的候选卡。没有写入 Anki。"
    "你可以修改材料或检查本次会话设置后重试。"
)

BEGINNER_AI_SETTINGS_HELP_COPY = (
    "请填写本次会话的 Provider、Base URL、模型和 API key，"
    "并确认你了解本次联网发送。当前不会写入 Anki。"
)

BEGINNER_AI_GENERATING_COPY = (
    "正在向所选 AI Provider 发送当前材料，请稍候。当前不会写入 Anki。"
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
Return this exact JSON shape:
{{"cards":[{{"front":"...","back":"...","source_excerpt":"..."}}]}}

Learning material:
{material_text}"""


class BeginnerAIDraftErrorCode(str, Enum):
    REQUEST_FAILED = "request_failed"
    MALFORMED_RESPONSE = "malformed_response"
    INVALID_CARD_PAYLOAD = "invalid_card_payload"
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

    drafts: tuple[BeginnerAICardDraft, ...] = field(
        default_factory=tuple,
        repr=False,
    )
    error_code: Optional[BeginnerAIDraftErrorCode] = None
    user_message: str = ""

    def __post_init__(self) -> None:
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
        if not isinstance(self.user_message, str):
            raise ValueError("user_message must be a string.")

    @property
    def success(self) -> bool:
        return bool(self.drafts) and self.error_code is None

    def to_safe_dict(self) -> dict:
        return {
            "success": self.success,
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
            return _failure(BeginnerAIDraftErrorCode.INVALID_CARD_PAYLOAD)
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
        except Exception:
            return _failure(BeginnerAIDraftErrorCode.REQUEST_FAILED)

        if not 200 <= response.status_code < 300:
            return _failure(BeginnerAIDraftErrorCode.REQUEST_FAILED)
        content = _extract_assistant_content(response.json_body)
        if content is None:
            return _failure(BeginnerAIDraftErrorCode.MALFORMED_RESPONSE)
        return parse_beginner_ai_card_drafts(content, max_cards=max_cards)


def parse_beginner_ai_card_drafts(
    json_text: str,
    max_cards: int = 5,
) -> BeginnerAICardDraftGenerationResult:
    """Parse a JSON array or {cards: [...]} into isolated draft models."""

    if not isinstance(json_text, str):
        return _failure(BeginnerAIDraftErrorCode.MALFORMED_RESPONSE)
    normalized = _strip_markdown_fence(json_text.strip())
    try:
        payload = json.loads(normalized)
    except (json.JSONDecodeError, TypeError):
        return _failure(BeginnerAIDraftErrorCode.MALFORMED_RESPONSE)

    cards = payload.get("cards") if isinstance(payload, dict) else payload
    if not isinstance(cards, list):
        return _failure(BeginnerAIDraftErrorCode.INVALID_CARD_PAYLOAD)
    if not cards:
        return _failure(BeginnerAIDraftErrorCode.NO_CARDS)

    drafts = []
    for index, card in enumerate(cards[:max_cards], start=1):
        if not isinstance(card, dict):
            return _failure(BeginnerAIDraftErrorCode.INVALID_CARD_PAYLOAD)
        front = _validated_text(card.get("front"), max_chars=500)
        back = _validated_text(card.get("back"), max_chars=4000)
        source_excerpt = _validated_text(
            card.get("source_excerpt") or card.get("rationale"),
            max_chars=1000,
        )
        if not all((front, back, source_excerpt)):
            return _failure(BeginnerAIDraftErrorCode.INVALID_CARD_PAYLOAD)
        drafts.append(
            BeginnerAICardDraft(
                id=f"ai-draft-{index}",
                front=front,
                back=back,
                source_excerpt=source_excerpt,
            )
        )

    return BeginnerAICardDraftGenerationResult(
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


def _strip_markdown_fence(text: str) -> str:
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def _validated_text(value: object, max_chars: int) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if not normalized or len(normalized) > max_chars:
        return ""
    return normalized


def _failure(
    code: BeginnerAIDraftErrorCode,
) -> BeginnerAICardDraftGenerationResult:
    return BeginnerAICardDraftGenerationResult(
        error_code=code,
        user_message=BEGINNER_AI_SAFE_ERROR_COPY,
    )
