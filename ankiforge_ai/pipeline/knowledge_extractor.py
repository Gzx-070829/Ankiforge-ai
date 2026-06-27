"""Mock knowledge point extraction service for the pipeline layer."""

import json
from typing import Iterable, List

from .knowledge_points import parse_knowledge_points_json
from .models import KnowledgePoint, SourceChunk


class MockKnowledgePointExtractor:
    """Build deterministic fake output without AI or network access."""

    def extract_from_chunk(self, chunk: SourceChunk) -> List[KnowledgePoint]:
        text = str(chunk.text or "").strip()
        if not text:
            return []

        title = _mock_title(chunk)
        payload = {
            "knowledge_points": [
                {
                    "title": title,
                    "explanation": text,
                    "evidence": text,
                    "tags": ["mock"],
                    "importance": "medium",
                }
            ]
        }
        json_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return parse_knowledge_points_json(json_text, chunk)


def extract_knowledge_points_from_chunks(
    chunks: Iterable[SourceChunk],
    extractor: MockKnowledgePointExtractor,
) -> List[KnowledgePoint]:
    knowledge_points = []
    for chunk in chunks:
        knowledge_points.extend(extractor.extract_from_chunk(chunk))
    return knowledge_points


def _mock_title(chunk: SourceChunk) -> str:
    for heading in reversed(chunk.heading_path):
        title = str(heading or "").strip()
        if title:
            return title
    return "Untitled"
