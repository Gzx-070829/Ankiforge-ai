"""Base types for AI card generation providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...importers.md_importer import MarkdownChunk
    from ..schemas import GeneratedCard


@dataclass
class AIProviderConfig:
    ai_provider: str = "mock"
    model: str = "mock-v0.1.2"
    api_base_url: str = ""
    max_cards_per_chunk: int = 3


class AIProvider(ABC):
    """Common interface for mock and future OpenAI-compatible providers."""

    name = "base"

    def __init__(self, config=None):
        self.config = config or AIProviderConfig()

    @abstractmethod
    def generate_cards(self, chunk: "MarkdownChunk") -> List["GeneratedCard"]:
        """Generate candidate cards for one Markdown chunk."""
