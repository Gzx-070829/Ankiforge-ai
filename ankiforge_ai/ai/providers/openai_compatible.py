"""OpenAI-compatible Chat Completions provider."""

import urllib.error
from typing import List

from ..prompts import SYSTEM_PROMPT, build_user_prompt, response_format_payload
from ..schemas import GeneratedCard
from ..validators import CardValidationError, cards_from_json_text
from ...pipeline.openai_compatible_http_transport import (
    OpenAICompatibleHTTPTransport,
)
from .base import AIProvider


class ProviderError(RuntimeError):
    """Raised for provider setup, network, HTTP, or response errors."""


class OpenAICompatibleProvider(AIProvider):
    """Generic provider for DeepSeek and other OpenAI-compatible APIs."""

    name = "openai_compatible"

    def generate_cards(self, chunk) -> List[GeneratedCard]:
        _validate_config(self.config)
        payload = build_chat_completions_payload(chunk, self.config)
        response = post_chat_completions(payload, self.config)
        content = extract_assistant_content(response)
        try:
            return cards_from_json_text(
                content,
                chunk,
                self.config.max_cards_per_chunk,
                self.config.ai_provider,
                self.config.model,
            )
        except CardValidationError:
            raise


def build_chat_completions_payload(chunk, config) -> dict:
    return {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(chunk, config.max_cards_per_chunk),
            },
        ],
        "temperature": config.temperature,
        "response_format": response_format_payload(),
    }


def post_chat_completions(payload: dict, config) -> dict:
    url = _chat_completions_url(config.api_base_url)
    try:
        response = OpenAICompatibleHTTPTransport().post_json(
            url=url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout_seconds=config.timeout_seconds,
        )
    except urllib.error.URLError:
        raise ProviderError("AI API 网络请求失败。") from None
    except TimeoutError:
        raise ProviderError("AI API 请求超时。") from None
    if not 200 <= response.status_code < 300:
        raise ProviderError(f"AI API HTTP {response.status_code}。")
    parsed = response.json_body
    if not isinstance(parsed, dict):
        raise ProviderError("AI API 响应不是合法 JSON object。")
    return parsed


def extract_assistant_content(response: dict) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ProviderError("AI API 响应缺少 choices[0].message.content。") from e

    if not isinstance(content, str) or not content.strip():
        raise ProviderError("AI API 返回了空内容。")
    return content.strip()


def _chat_completions_url(api_base_url: str) -> str:
    base = str(api_base_url or "").strip().rstrip("/")
    if not base:
        raise ProviderError("请填写 API Base URL，或切回 mock provider。")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _validate_config(config) -> None:
    if not str(config.api_key or "").strip():
        raise ProviderError("请填写 API key，或切回 mock provider。")
    if not str(config.model or "").strip():
        raise ProviderError("请填写模型名称。")
    if config.timeout_seconds <= 0:
        raise ProviderError("timeout_seconds 必须大于 0。")
