"""Base types for AI card generation providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...importers.md_importer import MarkdownChunk
    from ..schemas import GeneratedCard


@dataclass
class AIProviderConfig:
    ai_provider: str = "mock"
    model: str = "mock-v0.2"
    api_base_url: str = ""
    api_key: str = field(default="", repr=False)
    max_cards_per_chunk: int = 3
    timeout_seconds: int = 60
    temperature: float = 0.2


class AIProvider(ABC):
    """Common interface for mock and future OpenAI-compatible providers."""

    name = "base"

    def __init__(self, config=None):
        self.config = config or AIProviderConfig()

    @abstractmethod
    def generate_cards(self, chunk: "MarkdownChunk") -> List["GeneratedCard"]:
        """Generate candidate cards for one Markdown chunk."""
