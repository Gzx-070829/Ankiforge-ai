"""Offline orchestration for the complete mock import pipeline."""

from dataclasses import asdict, dataclass
from typing import Callable, Iterable, List, Optional

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

PIPELINE_RUN_STATUSES = {"success", "partial", "failed"}
PIPELINE_STAGES = {
    "source_analysis",
    "knowledge_extraction",
    "human_selection",
    "card_generation",
    "quality_gate",
    "human_review",
    "summary",
}


@dataclass
class PipelineRunResult:
    source_document: SourceDocument
    chunks: List[SourceChunk]
    knowledge_points: List[KnowledgePoint]
    human_selections: List[HumanSelection]
    card_candidates: List[CardCandidate]
    quality_results: List[QualityGateResult]
    human_reviews: List[HumanReview]


@dataclass
class PipelineRunSummary:
    source_filename: str
    source_document_id: str
    chunk_count: int
    knowledge_point_count: int
    human_selection_count: int
    selected_count: int
    rejected_count: int
    deferred_count: int
    card_candidate_count: int
    quality_passed_count: int
    quality_failed_count: int
    human_review_count: int
    pending_review_count: int
    approved_review_count: int
    rejected_review_count: int
    needs_edit_review_count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineRunStatus:
    status: str
    failed_stage: str = ""
    error_message: str = ""
    error_type: str = ""
    summary: Optional[PipelineRunSummary] = None

    def __post_init__(self) -> None:
        if self.status not in PIPELINE_RUN_STATUSES:
            raise ValueError("Pipeline run status must be success, partial, or failed.")
        if self.failed_stage and self.failed_stage not in PIPELINE_STAGES:
            raise ValueError("Pipeline run failed_stage is not recognized.")

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "failed_stage": self.failed_stage,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "summary": self.summary.to_dict() if self.summary else None,
        }


@dataclass
class PipelineRunWithStatus:
    result: Optional[PipelineRunResult]
    status: PipelineRunStatus


def summarize_pipeline_run(result: PipelineRunResult) -> PipelineRunSummary:
    return PipelineRunSummary(
        source_filename=result.source_document.file_name,
        source_document_id=result.source_document.document_id,
        chunk_count=len(result.chunks),
        knowledge_point_count=len(result.knowledge_points),
        human_selection_count=len(result.human_selections),
        selected_count=sum(
            selection.decision == "selected" for selection in result.human_selections
        ),
        rejected_count=sum(
            selection.decision == "rejected" for selection in result.human_selections
        ),
        deferred_count=sum(
            selection.decision == "deferred" for selection in result.human_selections
        ),
        card_candidate_count=len(result.card_candidates),
        quality_passed_count=sum(item.passed for item in result.quality_results),
        quality_failed_count=sum(not item.passed for item in result.quality_results),
        human_review_count=len(result.human_reviews),
        pending_review_count=sum(
            review.decision == "pending" for review in result.human_reviews
        ),
        approved_review_count=sum(
            review.decision == "approved" for review in result.human_reviews
        ),
        rejected_review_count=sum(
            review.decision == "rejected" for review in result.human_reviews
        ),
        needs_edit_review_count=sum(
            review.decision == "needs_edit" for review in result.human_reviews
        ),
    )


def extract_mock_knowledge_points(markdown_path: str) -> List[KnowledgePoint]:
    _, chunks = analyze_markdown_file(markdown_path)
    return extract_knowledge_points_from_chunks(
        chunks,
        MockKnowledgePointExtractor(),
    )


def run_full_mock_pipeline(
    markdown_path: str,
    selected_point_ids: Optional[Iterable[str]] = None,
) -> PipelineRunResult:
    return _execute_full_mock_pipeline(markdown_path, selected_point_ids)


def run_full_mock_pipeline_with_status(
    markdown_path: str,
    selected_point_ids: Optional[Iterable[str]] = None,
) -> PipelineRunWithStatus:
    state = {"stage": "source_analysis"}
    result = None

    def set_stage(stage: str) -> None:
        state["stage"] = stage

    try:
        result = _execute_full_mock_pipeline(
            markdown_path,
            selected_point_ids,
            stage_callback=set_stage,
        )
        set_stage("summary")
        summary = summarize_pipeline_run(result)
    except Exception as error:
        run_status = (
            "failed" if state["stage"] == "source_analysis" else "partial"
        )
        return PipelineRunWithStatus(
            result=result,
            status=PipelineRunStatus(
                status=run_status,
                failed_stage=state["stage"],
                error_message=str(error),
                error_type=type(error).__name__,
            ),
        )

    return PipelineRunWithStatus(
        result=result,
        status=PipelineRunStatus(status="success", summary=summary),
    )


def _execute_full_mock_pipeline(
    markdown_path: str,
    selected_point_ids: Optional[Iterable[str]] = None,
    stage_callback: Optional[Callable[[str], None]] = None,
) -> PipelineRunResult:
    def start_stage(stage: str) -> None:
        if stage_callback:
            stage_callback(stage)

    start_stage("source_analysis")
    source_document, chunks = analyze_markdown_file(markdown_path)

    start_stage("knowledge_extraction")
    knowledge_points = extract_knowledge_points_from_chunks(
        chunks,
        MockKnowledgePointExtractor(),
    )

    start_stage("human_selection")
    selection_ids = (
        [point.point_id for point in knowledge_points]
        if selected_point_ids is None
        else list(selected_point_ids)
    )
    human_selections = create_human_selections(knowledge_points, selection_ids)

    start_stage("card_generation")
    card_candidates = create_card_candidates(human_selections)

    start_stage("quality_gate")
    quality_results = run_quality_gate_for_candidates(card_candidates)

    start_stage("human_review")
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
