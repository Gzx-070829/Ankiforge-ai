"""Pure adapter between knowledge point selection UI and pipeline models."""

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from .human_selection import create_human_selections
from .models import HumanSelection, KnowledgePoint

SELECTION_PREVIEW_MAX_CHARS = 140


@dataclass(frozen=True)
class KnowledgePointPreviewItem:
    point_id: str
    title: str
    explanation: str
    importance: str
    tags: Tuple[str, ...]
    source_display: str
    evidence: str
    default_selected: bool = True


def build_knowledge_point_preview_items(
    points: Iterable[KnowledgePoint],
) -> List[KnowledgePointPreviewItem]:
    return [
        KnowledgePointPreviewItem(
            point_id=point.point_id,
            title=str(point.title or "").strip(),
            explanation=_preview_text(point.explanation),
            importance=str(point.importance or "").strip(),
            tags=tuple(point.tags),
            source_display=str(point.source_display or "").strip(),
            evidence=_preview_text(point.evidence),
        )
        for point in points
    ]


def create_selections_from_preview_choice(
    points: Iterable[KnowledgePoint],
    selected_point_ids: Iterable[str],
) -> List[HumanSelection]:
    return create_human_selections(points, selected_point_ids)


def _preview_text(text: str) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= SELECTION_PREVIEW_MAX_CHARS:
        return normalized
    return normalized[: SELECTION_PREVIEW_MAX_CHARS - 3].rstrip() + "..."
