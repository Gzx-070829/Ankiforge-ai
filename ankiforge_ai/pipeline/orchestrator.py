"""Offline orchestration for the complete mock import pipeline."""

from dataclasses import dataclass
from typing import Iterable, List, Optional

from .card_candidates import create_card_candidates
from .human_review import create_human_reviews
from .human_selection import create_human_selections
from .knowledge_extractor import (
    MockKnowledgePointExtractor,
    extract_knowledge_points_from_chunks,
)
from .models import (
    CardCandidate,
    HumanReview,
    HumanSelection,
    KnowledgePoint,
    QualityGateResult,
    SourceChunk,
    SourceDocument,
)
from .quality_gate import run_quality_gate_for_candidates
from .source_analyzer import analyze_markdown_file


@dataclass
class PipelineRunResult:
    source_document: SourceDocument
    chunks: List[SourceChunk]
    knowledge_points: List[KnowledgePoint]
    human_selections: List[HumanSelection]
    card_candidates: List[CardCandidate]
    quality_results: List[QualityGateResult]
    human_reviews: List[HumanReview]


def run_full_mock_pipeline(
    markdown_path: str,
    selected_point_ids: Optional[Iterable[str]] = None,
) -> PipelineRunResult:
    source_document, chunks = analyze_markdown_file(markdown_path)
    knowledge_points = extract_knowledge_points_from_chunks(
        chunks,
        MockKnowledgePointExtractor(),
    )
    selection_ids = (
        [point.point_id for point in knowledge_points]
        if selected_point_ids is None
        else list(selected_point_ids)
    )
    human_selections = create_human_selections(knowledge_points, selection_ids)
    card_candidates = create_card_candidates(human_selections)
    quality_results = run_quality_gate_for_candidates(card_candidates)
    human_reviews = create_human_reviews(card_candidates, quality_results)

    return PipelineRunResult(
        source_document=source_document,
        chunks=chunks,
        knowledge_points=knowledge_points,
        human_selections=human_selections,
        card_candidates=card_candidates,
        quality_results=quality_results,
        human_reviews=human_reviews,
    )
