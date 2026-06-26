"""Provider registry for AnkiForge AI card generation."""

from .base import AIProvider, AIProviderConfig
from .mock_provider import MockAIProvider


def create_provider(config):
    """Return the configured provider.

    v0.1.2 intentionally ships only the mock provider. The registry keeps the
    future OpenAI-compatible providers isolated from the UI and importer code.
    """
    provider_name = (config.ai_provider or "mock").strip().lower()
    if provider_name == MockAIProvider.name:
        return MockAIProvider(config)

    raise ValueError(
        "v0.1.2 仅支持 mock provider；当前配置为 "
        f"'{config.ai_provider}'。请将 ai_provider 改为 'mock'。"
    )


__all__ = ["AIProvider", "AIProviderConfig", "MockAIProvider", "create_provider"]
