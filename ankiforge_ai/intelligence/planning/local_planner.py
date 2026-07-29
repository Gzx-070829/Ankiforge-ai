"""Balanced, deterministic planning over existing structural chunks."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import deque
from itertools import islice

from ...document import BlockKind, DocumentIR

from ..analyzer import analyze_document
from ..chunking import DocumentChunk
from ..models import DocumentAnalysis
from ..template_router import route_template
from .models import KnowledgePlan, KnowledgePointPlan


MAX_PLAN_POINTS = 96
_DEFINITION = re.compile(
    r"(?:\b(?:means|defined\s+as|refers\s+to)\b"
    r"|\b(?:is|are)\s+(?:an?\s+|the\s+type\s+of\b|types?\s+of\b)"
    r"|(?:定义为|是指|指的是))",
    re.IGNORECASE,
)
_COMPARISON = re.compile(
    r"(?:\b(?:unlike|versus|whereas|difference)\b|(?:相比|区别|不同于|对比))",
    re.IGNORECASE,
)
_PROCESS_STAGE = re.compile(
    r"(?:\b(?:first|then|next|finally|step)\b|(?:首先|然后|最后|步骤))",
    re.IGNORECASE,
)


def build_local_knowledge_plan(
    document: DocumentIR,
    chunks,
    analysis: DocumentAnalysis | None = None,
    *,
    max_points: int | None = None,
) -> KnowledgePlan:
    resolved_chunks = _validated_chunks(document, chunks)
    resolved_analysis = analyze_document(document) if analysis is None else analysis
    if not isinstance(resolved_analysis, DocumentAnalysis):
        raise TypeError("analysis must be a DocumentAnalysis or None")
    if resolved_analysis.document_id != document.document_id:
        raise ValueError("analysis document does not match the plan document")
    if max_points is None:
        point_limit = min(
            MAX_PLAN_POINTS,
            resolved_analysis.estimated_knowledge_points,
        )
    else:
        if (
            isinstance(max_points, bool)
            or not isinstance(max_points, int)
            or not 0 <= max_points <= MAX_PLAN_POINTS
        ):
            raise ValueError("max_points must be within the plan limit")
        point_limit = max_points

    queues = {
        section.section_id: deque()
        for section in document.sections
    }
    for chunk in resolved_chunks:
        queues[chunk.section_id].append(chunk)
    selected = []
    seen_titles = set()
    section_counts = {section.section_id: 0 for section in document.sections}
    candidate_index = 0
    active_sections = [section.section_id for section in document.sections]
    while active_sections and len(selected) < point_limit:
        next_active = []
        for section_id in active_sections:
            queue = queues[section_id]
            if not queue:
                continue
            chunk = queue.popleft()
            if queue:
                next_active.append(section_id)
            title = _candidate_title(chunk)
            if title is None:
                continue
            normalized_title = normalize_point_text(title)
            if not normalized_title or normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)
            point_type = _point_type(chunk, title)
            route = route_template(
                resolved_analysis,
                requested_mode="auto",
                point_type=point_type,
                block_kinds=chunk.block_kinds,
            )
            point_digest = hashlib.sha256(
                "\x1f".join(
                    (
                        document.document_id,
                        chunk.chunk_id,
                        str(candidate_index),
                    )
                ).encode("utf-8")
            ).hexdigest()[:16]
            selected.append(
                KnowledgePointPlan(
                    point_id="point-" + point_digest,
                    title=title,
                    point_type=point_type,
                    priority=(
                        "high" if section_counts[section_id] == 0 else "medium"
                    ),
                    section_id=section_id,
                    source_chunk_ids=(chunk.chunk_id,),
                    source_locations=chunk.source_locations,
                    recommended_template=route.template_id,
                    rationale=route.reason_code,
                )
            )
            section_counts[section_id] += 1
            candidate_index += 1
            if len(selected) >= point_limit:
                break
        active_sections = next_active

    chunk_ids = tuple(chunk.chunk_id for chunk in resolved_chunks)
    plan_digest = hashlib.sha256(
        "\x1f".join((document.document_id, "local", *chunk_ids)).encode("utf-8")
    ).hexdigest()[:16]
    return KnowledgePlan(
        plan_id="plan-" + plan_digest,
        document_id=document.document_id,
        source="local",
        chunk_ids=chunk_ids,
        points=tuple(selected),
    )


def normalize_point_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _candidate_title(chunk: DocumentChunk) -> str | None:
    lines = [
        line.strip()
        for line in chunk.text.splitlines()
        if line.strip() and not line.lstrip().startswith("# ")
    ]
    if not lines:
        return None
    if BlockKind.TABLE in chunk.block_kinds and len(lines) > 1:
        candidate = lines[1]
    else:
        candidate = lines[0]
    candidate = candidate.lstrip("-*+ ").strip()
    if not candidate:
        return None
    return candidate[:240]


def _point_type(chunk: DocumentChunk, title: str) -> str:
    kinds = set(chunk.block_kinds)
    if BlockKind.FORMULA in kinds:
        return "formula"
    if BlockKind.CODE in kinds:
        return "code"
    if BlockKind.TABLE in kinds:
        return "table"
    if BlockKind.TRANSCRIPT in kinds:
        return "transcript"
    if _COMPARISON.search(title):
        return "comparison"
    if sum(1 for _ in _PROCESS_STAGE.finditer(title)) >= 2:
        return "process"
    if _DEFINITION.search(title):
        return "definition"
    return "concept"


def _validated_chunks(
    document: DocumentIR,
    chunks,
) -> tuple[DocumentChunk, ...]:
    if not isinstance(document, DocumentIR):
        raise TypeError("document must be a DocumentIR")
    if isinstance(chunks, (str, bytes)):
        raise TypeError("chunks must be an iterable of DocumentChunk instances")
    try:
        resolved = tuple(islice(iter(chunks), 49))
    except TypeError:
        raise TypeError(
            "chunks must be an iterable of DocumentChunk instances"
        ) from None
    if len(resolved) > 48:
        raise ValueError("chunks must contain at most 48 DocumentChunk instances")
    if not all(isinstance(chunk, DocumentChunk) for chunk in resolved):
        raise ValueError("chunks must contain at most 48 DocumentChunk instances")
    ids = tuple(chunk.chunk_id for chunk in resolved)
    if len(set(ids)) != len(ids):
        raise ValueError("chunk IDs must be unique")
    section_ids = {section.section_id for section in document.sections}
    block_ids = {
        block.block_id
        for section in document.sections
        for block in section.blocks
    }
    for chunk in resolved:
        if chunk.document_id != document.document_id:
            raise ValueError("chunk document does not match plan document")
        if chunk.section_id not in section_ids:
            raise ValueError("chunk references an unknown section")
        if any(block_id not in block_ids for block_id in chunk.block_ids):
            raise ValueError("chunk references an unknown document block")
    return resolved
