"""Pipeline-style adapter for AI-backed knowledge point extraction."""

from typing import Iterable, List

from .ai_extraction_service import (
    KnowledgePointExtractionOutcome,
    extract_knowledge_points,
    extract_knowledge_points_from_chunks,
)
from .ai_provider_contracts import KnowledgePointJSONProvider
from .models import SourceChunk


class AIKnowledgePointExtractor:
    """Delegate knowledge point extraction to an injected JSON provider."""

    def __init__(self, provider: KnowledgePointJSONProvider):
        self._provider = provider

    def extract_from_chunk(
        self,
        chunk: SourceChunk,
    ) -> KnowledgePointExtractionOutcome:
        return extract_knowledge_points(chunk, self._provider)

    def extract_from_chunks(
        self,
        chunks: Iterable[SourceChunk],
    ) -> List[KnowledgePointExtractionOutcome]:
        return extract_knowledge_points_from_chunks(chunks, self._provider)
