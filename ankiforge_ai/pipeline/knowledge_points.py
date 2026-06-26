"""Parsing and validation for extracted knowledge point JSON."""

import hashlib
import json
from typing import List

from .models import KnowledgePoint, SourceChunk

DEFAULT_IMPORTANCE = "medium"


def parse_knowledge_points_json(text: str, source_chunk: SourceChunk) -> List[KnowledgePoint]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid knowledge point JSON: {e}") from e

    return parse_knowledge_points_payload(payload, source_chunk)


def parse_knowledge_points_payload(payload, source_chunk: SourceChunk) -> List[KnowledgePoint]:
    items = _extract_items(payload)
    knowledge_points = []

    for ordinal, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Knowledge point at index {ordinal} must be an object.")

        title = _required_text(item.get("title"), "title", ordinal)
        explanation = _required_text(item.get("explanation"), "explanation", ordinal)
        evidence = _optional_text(item.get("evidence"))
        importance = _optional_text(item.get("importance")) or DEFAULT_IMPORTANCE
        tags = _validate_tags(item.get("tags"), ordinal)

        knowledge_points.append(
            KnowledgePoint(
                point_id=build_knowledge_point_id(
                    source_chunk.chunk_id,
                    ordinal,
                    title,
                    explanation,
                ),
                document_id=source_chunk.document_id,
                chunk_id=source_chunk.chunk_id,
                source_display=source_chunk.source_display,
                heading_path=list(source_chunk.heading_path),
                ordinal=ordinal,
                title=title,
                explanation=explanation,
                evidence=evidence,
                tags=tags,
                importance=importance,
            )
        )

    return knowledge_points


def build_knowledge_point_id(
    chunk_id: str,
    ordinal: int,
    title: str,
    explanation: str,
) -> str:
    short_hash = _short_hash(f"{title}\n{explanation}")
    return f"kp_{chunk_id}_{ordinal}_{short_hash}"


def _extract_items(payload) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get("knowledge_points")
        if isinstance(items, list):
            return items
        raise ValueError("Knowledge point payload object must contain a knowledge_points list.")
    raise ValueError("Knowledge point payload must be a list or an object with knowledge_points.")


def _required_text(value, field_name: str, ordinal: int) -> str:
    text = _optional_text(value)
    if not text:
        raise ValueError(f"Knowledge point at index {ordinal} missing required {field_name}.")
    return text


def _optional_text(value) -> str:
    return str(value or "").strip()


def _validate_tags(value, ordinal: int) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Knowledge point at index {ordinal} tags must be a list.")
    return [str(tag).strip() for tag in value if str(tag).strip()]


def _short_hash(text: str) -> str:
    normalized = " ".join(str(text or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
