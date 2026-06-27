"""Deterministic non-network provider for pipeline contract tests."""

import json
from typing import Optional

from .ai_provider_contracts import (
    AIProviderError,
    AIProviderMetadata,
    AIProviderResult,
    KnowledgePointExtractionRequest,
    KnowledgePointExtractionResponse,
    build_knowledge_point_extraction_request,
)
from .models import SourceChunk


class FakeAIProvider:
    """Produce parser-compatible fake JSON without prompts or network access."""

    def __init__(self, failure: Optional[AIProviderError] = None):
        self.metadata = AIProviderMetadata(
            provider_id="fake",
            model="fake-knowledge-v0.5",
        )
        self._failure = failure

    def extract_from_chunk(self, chunk: SourceChunk) -> AIProviderResult:
        return self.extract(build_knowledge_point_extraction_request(chunk))

    def extract(
        self,
        request: KnowledgePointExtractionRequest,
    ) -> AIProviderResult:
        if self._failure is not None:
            return AIProviderResult.from_error(request, self._failure)

        text = request.text.strip()
        knowledge_points = []
        if text:
            knowledge_points.append(
                {
                    "title": _fake_title(request),
                    "explanation": text,
                    "evidence": text,
                    "tags": ["fake"],
                    "importance": "medium",
                }
            )

        json_text = json.dumps(
            {"knowledge_points": knowledge_points},
            ensure_ascii=False,
            sort_keys=True,
        )
        response = KnowledgePointExtractionResponse(
            request_id=request.request_id,
            chunk_id=request.chunk_id,
            metadata=self.metadata,
            json_text=json_text,
        )
        return AIProviderResult.from_response(response)


def _fake_title(request: KnowledgePointExtractionRequest) -> str:
    for heading in reversed(request.heading_path):
        title = str(heading or "").strip()
        if title:
            return title
    return "Untitled"
