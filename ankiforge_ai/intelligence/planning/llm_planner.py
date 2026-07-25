"""Strict parser for caller-supplied planner JSON; performs no Provider call."""

import hashlib
import json
from collections.abc import Mapping
from itertools import islice

from ankiforge_ai.document import DocumentIR

from ..chunking import DocumentChunk
from .local_planner import (
    MAX_PLAN_POINTS,
    _validated_chunks,
    build_local_knowledge_plan,
    normalize_point_text,
)
from .models import (
    MAX_POINT_SOURCE_CHUNKS,
    SUPPORTED_POINT_TYPES,
    SUPPORTED_TEMPLATES,
    KnowledgePlan,
    KnowledgePointPlan,
)


_POINT_FIELDS = {
    "title",
    "point_type",
    "priority",
    "source_chunk_ids",
    "recommended_template",
    "rationale",
}
MAX_LLM_PLAN_JSON_CHARS = 256_000


def parse_llm_knowledge_plan(
    payload,
    document: DocumentIR,
    chunks,
    *,
    fallback_plan: KnowledgePlan | None = None,
) -> KnowledgePlan:
    resolved_chunks = _validated_chunks(document, chunks)
    local_fallback = build_local_knowledge_plan(document, resolved_chunks)
    fallback = (
        fallback_plan
        if _is_valid_fallback(
            fallback_plan,
            document,
            resolved_chunks,
        )
        else local_fallback
    )
    try:
        return _parse_payload(payload, document, resolved_chunks)
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
        UnicodeError,
        RecursionError,
    ):
        return fallback


def _parse_payload(
    payload,
    document: DocumentIR,
    chunks: tuple[DocumentChunk, ...],
) -> KnowledgePlan:
    if isinstance(payload, str):
        if len(payload) > MAX_LLM_PLAN_JSON_CHARS:
            raise ValueError("planner JSON exceeds its bounded size")
        value = json.loads(payload)
    elif isinstance(payload, Mapping):
        value = payload
    else:
        raise TypeError("planner result must be JSON text or a mapping")
    if not _has_exact_keys(value, {"points"}):
        raise ValueError("planner result must contain only a points list")
    raw_points = _mapping_value(value, "points")
    if not isinstance(raw_points, list):
        raise ValueError("planner result must contain only a points list")
    if not 1 <= len(raw_points) <= MAX_PLAN_POINTS:
        raise ValueError("planner points exceed the bounded plan size")

    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    points = []
    seen_titles = set()
    for raw in raw_points:
        if not _has_exact_keys(raw, _POINT_FIELDS):
            raise ValueError("planner point fields are invalid")
        title = _bounded_string(_mapping_value(raw, "title"), "title", 240)
        point_type = _bounded_string(
            _mapping_value(raw, "point_type"),
            "point_type",
            40,
        )
        priority = _bounded_string(
            _mapping_value(raw, "priority"),
            "priority",
            12,
        )
        template = _bounded_string(
            _mapping_value(raw, "recommended_template"),
            "recommended_template",
            64,
        )
        rationale = _bounded_string(
            _mapping_value(raw, "rationale"),
            "rationale",
            240,
        )
        if point_type not in SUPPORTED_POINT_TYPES:
            raise ValueError("planner point_type is unsupported")
        if priority not in {"high", "medium", "low"}:
            raise ValueError("planner priority is unsupported")
        if template not in SUPPORTED_TEMPLATES:
            raise ValueError("planner template is unsupported")
        raw_chunk_ids = _mapping_value(raw, "source_chunk_ids")
        if (
            not isinstance(raw_chunk_ids, list)
            or not 1 <= len(raw_chunk_ids) <= MAX_POINT_SOURCE_CHUNKS
            or not all(isinstance(item, str) for item in raw_chunk_ids)
        ):
            raise ValueError("planner source_chunk_ids are invalid")
        source_chunk_ids = tuple(raw_chunk_ids)
        if (
            len(set(source_chunk_ids)) != len(source_chunk_ids)
            or any(chunk_id not in by_id for chunk_id in source_chunk_ids)
        ):
            raise ValueError("planner source chunk is unknown")
        source_chunks = tuple(by_id[chunk_id] for chunk_id in source_chunk_ids)
        section_ids = {chunk.section_id for chunk in source_chunks}
        if len(section_ids) != 1:
            raise ValueError("one planner point must remain within one section")
        normalized_title = normalize_point_text(title)
        if not normalized_title or not any(
            normalized_title in normalize_point_text(chunk.text)
            for chunk in source_chunks
        ):
            raise ValueError("planner point is not grounded in source chunks")
        if normalized_title in seen_titles:
            raise ValueError("planner points contain duplicate normalized evidence")
        seen_titles.add(normalized_title)
        locations = _ordered_locations(source_chunks)
        point_digest = hashlib.sha256(
            "\x1f".join(
                (
                    document.document_id,
                    "llm",
                    str(len(points)),
                    *source_chunk_ids,
                )
            ).encode("utf-8")
        ).hexdigest()[:16]
        points.append(
            KnowledgePointPlan(
                point_id="point-" + point_digest,
                title=title,
                point_type=point_type,
                priority=priority,
                section_id=source_chunks[0].section_id,
                source_chunk_ids=source_chunk_ids,
                source_locations=locations,
                recommended_template=template,
                rationale=rationale,
            )
        )
    if not points:
        raise ValueError("planner result contained no unique grounded points")
    chunk_ids = tuple(chunk.chunk_id for chunk in chunks)
    plan_digest = hashlib.sha256(
        "\x1f".join((document.document_id, "llm", *chunk_ids)).encode("utf-8")
    ).hexdigest()[:16]
    return KnowledgePlan(
        plan_id="plan-" + plan_digest,
        document_id=document.document_id,
        source="llm",
        chunk_ids=chunk_ids,
        points=tuple(points),
    )


def _bounded_string(value, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"planner {name} must be a bounded string")
    return value.strip()


def _has_exact_keys(value, expected: set[str]) -> bool:
    if not isinstance(value, Mapping):
        return False
    try:
        if len(value) != len(expected):
            return False
        keys = tuple(islice(iter(value), len(expected) + 1))
        return len(keys) == len(expected) and set(keys) == expected
    except Exception:
        return False


def _mapping_value(value: Mapping, key: str):
    try:
        return value[key]
    except Exception:
        raise ValueError("planner mapping could not be read safely") from None


def _ordered_locations(chunks) -> tuple:
    result = []
    seen = set()
    for chunk in chunks:
        for location in chunk.source_locations:
            if location not in seen:
                seen.add(location)
                result.append(location)
    return tuple(result)


def _is_valid_fallback(
    plan,
    document: DocumentIR,
    chunks: tuple[DocumentChunk, ...],
) -> bool:
    if (
        not isinstance(plan, KnowledgePlan)
        or plan.source != "local"
        or plan.document_id != document.document_id
        or plan.chunk_ids != tuple(chunk.chunk_id for chunk in chunks)
    ):
        return False
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    seen_titles = set()
    for point in plan.points:
        source_chunks = tuple(
            by_id.get(chunk_id) for chunk_id in point.source_chunk_ids
        )
        normalized = normalize_point_text(point.title)
        if (
            any(chunk is None for chunk in source_chunks)
            or not 1 <= len(source_chunks) <= MAX_POINT_SOURCE_CHUNKS
            or point.point_type not in SUPPORTED_POINT_TYPES
            or point.recommended_template not in SUPPORTED_TEMPLATES
            or not all(
                chunk.section_id == point.section_id
                for chunk in source_chunks
            )
            or not normalized
            or not any(
                normalized in normalize_point_text(chunk.text)
                for chunk in source_chunks
            )
            or point.source_locations != _ordered_locations(source_chunks)
            or normalized in seen_titles
        ):
            return False
        seen_titles.add(normalized)
    return True
