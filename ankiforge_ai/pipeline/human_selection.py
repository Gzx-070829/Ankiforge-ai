"""Helpers for recording human knowledge point selections."""

from typing import Iterable, List

from .models import HumanSelection, KnowledgePoint

VALID_DECISIONS = {"selected", "rejected", "deferred"}


def build_selection_id(point_id: str) -> str:
    return f"hs_{point_id}"


def create_human_selection(
    point: KnowledgePoint,
    decision: str = "selected",
    note: str = "",
) -> HumanSelection:
    if decision not in VALID_DECISIONS:
        raise ValueError(
            "Invalid human selection decision. "
            "Expected selected, rejected, or deferred."
        )

    return HumanSelection(
        selection_id=build_selection_id(point.point_id),
        point_id=point.point_id,
        document_id=point.document_id,
        chunk_id=point.chunk_id,
        source_display=point.source_display,
        heading_path=list(point.heading_path),
        ordinal=point.ordinal,
        title=point.title,
        explanation=point.explanation,
        evidence=point.evidence,
        tags=list(point.tags),
        importance=point.importance,
        decision=decision,
        note=note,
    )


def create_human_selections(
    points: Iterable[KnowledgePoint],
    selected_point_ids: Iterable[str],
) -> List[HumanSelection]:
    point_list = list(points)
    selected_ids = set(selected_point_ids)
    known_ids = {point.point_id for point in point_list}
    unknown_ids = selected_ids - known_ids
    if unknown_ids:
        unknown_text = ", ".join(sorted(str(point_id) for point_id in unknown_ids))
        raise ValueError(f"Unknown selected knowledge point IDs: {unknown_text}")

    return [
        create_human_selection(point)
        for point in point_list
        if point.point_id in selected_ids
    ]
