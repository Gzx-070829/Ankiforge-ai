"""Pure read-only adapter for displaying pipeline run outcomes."""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .orchestrator import PipelineRunWithStatus

PREVIEW_MAX_CHARS = 120


@dataclass(frozen=True)
class ReadOnlyCardPreviewItem:
    candidate_id: str
    front_preview: str
    back_preview: str
    quality_passed: Optional[bool]
    quality_issue_count: Optional[int]
    review_decision: str


@dataclass(frozen=True)
class ReadOnlyPipelinePreviewData:
    run_status: str
    failed_stage: str
    error_message: str
    summary_counts: Dict[str, int]
    cards: Tuple[ReadOnlyCardPreviewItem, ...]


def build_read_only_pipeline_preview(
    outcome: PipelineRunWithStatus,
) -> ReadOnlyPipelinePreviewData:
    summary_counts = {}
    if outcome.status.summary is not None:
        summary_counts = {
            key: value
            for key, value in outcome.status.summary.to_dict().items()
            if key.endswith("_count")
        }

    cards = []
    if outcome.result is not None:
        quality_by_id = {
            item.candidate_id: item for item in outcome.result.quality_results
        }
        review_by_id = {
            item.candidate_id: item for item in outcome.result.human_reviews
        }
        for candidate in outcome.result.card_candidates:
            quality = quality_by_id.get(candidate.candidate_id)
            review = review_by_id.get(candidate.candidate_id)
            cards.append(
                ReadOnlyCardPreviewItem(
                    candidate_id=candidate.candidate_id,
                    front_preview=_preview_text(candidate.front),
                    back_preview=_preview_text(candidate.back),
                    quality_passed=quality.passed if quality is not None else None,
                    quality_issue_count=(
                        len(quality.issues) if quality is not None else None
                    ),
                    review_decision=review.decision if review is not None else "",
                )
            )

    return ReadOnlyPipelinePreviewData(
        run_status=outcome.status.status,
        failed_stage=outcome.status.failed_stage,
        error_message=outcome.status.error_message,
        summary_counts=summary_counts,
        cards=tuple(cards),
    )


def _preview_text(text: str) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= PREVIEW_MAX_CHARS:
        return normalized
    return normalized[: PREVIEW_MAX_CHARS - 3].rstrip() + "..."
