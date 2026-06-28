"""Explicit wiring helpers for OpenAI-compatible pipeline providers."""

from typing import Optional

from .ai_knowledge_extractor_adapter import AIKnowledgePointExtractor
from .ai_provider_contracts import KnowledgePointJSONProvider
from .openai_compatible_http_transport import OpenAICompatibleHTTPTransport
from .openai_compatible_provider import (
    OpenAICompatibleKnowledgePointProvider,
    OpenAICompatibleProviderConfig,
    OpenAICompatibleTransport,
)
from .provider_safety_wrapper import SafeKnowledgePointJSONProvider


def create_openai_compatible_knowledge_point_provider(
    config: OpenAICompatibleProviderConfig,
    transport: Optional[OpenAICompatibleTransport] = None,
    wrap_safe: bool = True,
) -> KnowledgePointJSONProvider:
    """Assemble an OpenAI-compatible provider without invoking it."""
    resolved_transport = (
        OpenAICompatibleHTTPTransport() if transport is None else transport
    )
    provider = OpenAICompatibleKnowledgePointProvider(config, resolved_transport)
    if wrap_safe:
        return SafeKnowledgePointJSONProvider(provider)
    return provider


def create_openai_compatible_knowledge_point_extractor(
    config: OpenAICompatibleProviderConfig,
    transport: Optional[OpenAICompatibleTransport] = None,
    wrap_safe: bool = True,
) -> AIKnowledgePointExtractor:
    """Assemble an AI extractor through the provider factory."""
    provider = create_openai_compatible_knowledge_point_provider(
        config,
        transport=transport,
        wrap_safe=wrap_safe,
    )
    return AIKnowledgePointExtractor(provider)
