"""
Card schema + compatibility helpers for AnkiForge AI.

`GeneratedCard` is the unit everything else (preview table, Anki writer)
operates on. v0.2 keeps mock generation as the default, but routes it
through `ai.providers` so future OpenAI-compatible providers can be added
without changing importer, preview, or writer code.
"""

from dataclasses import dataclass, field
from typing import List

from ..importers.md_importer import MarkdownChunk


@dataclass
class GeneratedCard:
    card_type: str  # "basic" or "cloze"
    front: str
    back: str
    extra: str = ""
    tags: List[str] = field(default_factory=list)
    source: str = ""
    approved: bool = True


def mock_generate_cards(chunk: MarkdownChunk) -> List[GeneratedCard]:
    """
    Backward-compatible wrapper for older code paths.

    Produces one Basic card per chunk locally, with no network calls and no
    API key. New UI code should use `ai.providers.create_provider()`.
    """
    from .providers.base import AIProviderConfig
    from .providers.mock_provider import MockAIProvider

    return MockAIProvider(AIProviderConfig()).generate_cards(chunk)
