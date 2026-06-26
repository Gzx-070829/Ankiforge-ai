"""Provider registry for AnkiForge AI card generation."""

from .base import AIProvider, AIProviderConfig
from .mock_provider import MockAIProvider
from .openai_compatible import OpenAICompatibleProvider


def create_provider(config):
    """Return the configured provider.

    v0.2 keeps mock as the default safe provider. DeepSeek is a preset that
    reuses the same OpenAI-compatible implementation.
    """
    provider_name = (config.ai_provider or "mock").strip().lower()
    if provider_name == MockAIProvider.name:
        return MockAIProvider(config)
    if provider_name in {"deepseek", OpenAICompatibleProvider.name}:
        return OpenAICompatibleProvider(config)

    raise ValueError(
        "v0.2 支持 mock、deepseek、openai_compatible；当前配置为 "
        f"'{config.ai_provider}'。"
    )


__all__ = [
    "AIProvider",
    "AIProviderConfig",
    "MockAIProvider",
    "OpenAICompatibleProvider",
    "create_provider",
]
