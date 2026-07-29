"""Conservative deterministic call/card estimates for one bounded run."""

from __future__ import annotations

import math
from itertools import islice

from .chunking import DocumentChunk
from .models import DocumentAnalysis, IntelligenceLevel, PlanEstimate
from .planning.models import KnowledgePlan


MAX_AI_CALLS_PER_RUN = 12
MAX_DOCUMENT_CHUNKS = 48


def estimate_generation(
    analysis: DocumentAnalysis,
    chunks,
    *,
    level: IntelligenceLevel | str = IntelligenceLevel.STANDARD,
    plan: KnowledgePlan | None = None,
) -> PlanEstimate:
    if not isinstance(analysis, DocumentAnalysis):
        raise TypeError("analysis must be a DocumentAnalysis")
    try:
        resolved_level = IntelligenceLevel(level)
    except (TypeError, ValueError) as exc:
        raise ValueError("level must be fast, standard, or deep") from exc
    if isinstance(chunks, (str, bytes)):
        raise TypeError("chunks must contain DocumentChunk instances")
    try:
        resolved_chunks = tuple(
            islice(iter(chunks), MAX_DOCUMENT_CHUNKS + 1)
        )
    except TypeError:
        raise TypeError("chunks must contain DocumentChunk instances") from None
    if len(resolved_chunks) > MAX_DOCUMENT_CHUNKS:
        raise ValueError("chunk count exceeds MAX_DOCUMENT_CHUNKS")
    if not all(isinstance(chunk, DocumentChunk) for chunk in resolved_chunks):
        raise TypeError("chunks must contain DocumentChunk instances")
    if any(chunk.document_id != analysis.document_id for chunk in resolved_chunks):
        raise ValueError("chunks do not match the analyzed document")
    if plan is not None and (
        not isinstance(plan, KnowledgePlan)
        or plan.document_id != analysis.document_id
    ):
        raise ValueError("plan does not match the analyzed document")

    base_points = (
        len(plan.points) if plan is not None else analysis.estimated_knowledge_points
    )
    if base_points == 0:
        card_min = card_max = 0
    elif resolved_level is IntelligenceLevel.FAST:
        card_min = max(1, math.ceil(base_points * 0.5))
        card_max = base_points
    elif resolved_level is IntelligenceLevel.STANDARD:
        card_min = max(1, math.ceil(base_points * 0.75))
        card_max = min(96, max(card_min, math.ceil(base_points * 1.25)))
    else:
        card_min = base_points
        card_max = min(96, max(card_min, math.ceil(base_points * 1.5)))

    call_min, call_max = {
        IntelligenceLevel.FAST: (1, 3),
        IntelligenceLevel.STANDARD: (3, 8),
        IntelligenceLevel.DEEP: (4, MAX_AI_CALLS_PER_RUN),
    }[resolved_level]
    return PlanEstimate(
        level=resolved_level,
        chunk_count=len(resolved_chunks),
        estimated_card_min=card_min,
        estimated_card_max=card_max,
        estimated_call_min=call_min,
        estimated_call_max=call_max,
        max_calls=MAX_AI_CALLS_PER_RUN,
        requires_confirmation=resolved_level is not IntelligenceLevel.FAST,
    )
