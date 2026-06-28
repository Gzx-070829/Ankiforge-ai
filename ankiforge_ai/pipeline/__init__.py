"""Import pipeline foundation for AnkiForge AI."""

from .ai_provider_contracts import (
    AIProviderError,
    AIProviderMetadata,
    AIProviderResult,
    KnowledgePointExtractionRequest,
    KnowledgePointExtractionResponse,
    KnowledgePointJSONProvider,
    build_knowledge_point_extraction_request,
)
from .ai_extraction_service import (
    KnowledgePointExtractionOutcome,
    extract_knowledge_points,
    extract_knowledge_points_from_chunks as extract_ai_knowledge_points_from_chunks,
)
from .ai_knowledge_extractor_adapter import AIKnowledgePointExtractor
from .card_candidates import (
    build_candidate_id,
    create_card_candidate,
    create_card_candidates,
)
from .card_candidate_preview_adapter import (
    CardCandidatePreviewItem,
    QualityIssuePreviewItem,
    QualityReviewPreviewState,
    build_card_candidate_preview_item,
    build_card_candidate_preview_items,
    build_quality_review_preview_state,
)
from .controlled_write_bridge import (
    PipelineWriteEligibility,
    WriteReadyPreviewItem,
    build_pipeline_write_eligibility,
    build_write_ready_preview_item,
    build_write_ready_preview_items,
)
from .fake_ai_provider import FakeAIProvider
from .human_selection import (
    build_selection_id,
    create_human_selection,
    create_human_selections,
)
from .human_review import (
    build_review_id,
    create_human_review,
    create_human_reviews,
)
from .knowledge_extractor import (
    MockKnowledgePointExtractor,
    extract_knowledge_points_from_chunks,
)
from .knowledge_points import (
    build_knowledge_point_id,
    parse_knowledge_points_json,
    parse_knowledge_points_payload,
)
from .models import (
    CardCandidate,
    HumanReview,
    HumanSelection,
    KnowledgePoint,
    QualityGateResult,
    QualityIssue,
    SourceChunk,
    SourceDocument,
)
from .orchestrator import (
    PipelineRunResult,
    PipelineRunStatus,
    PipelineRunSummary,
    PipelineRunWithStatus,
    extract_mock_knowledge_points,
    run_full_mock_pipeline,
    run_full_mock_pipeline_with_status,
    summarize_pipeline_run,
)
from .openai_compatible_provider import (
    OpenAICompatibleKnowledgePointProvider,
    OpenAICompatibleProviderConfig,
    OpenAICompatibleTransport,
    OpenAICompatibleTransportResponse,
    build_chat_completions_payload,
    build_chat_completions_url,
)
from .preview_adapter import (
    ReadOnlyCardPreviewItem,
    ReadOnlyPipelinePreviewData,
    build_read_only_pipeline_preview,
)
from .provider_safety_wrapper import SafeKnowledgePointJSONProvider
from .quality_gate import (
    run_quality_gate,
    run_quality_gate_for_candidates,
    validate_quality_issue,
)
from .selection_bridge_adapter import (
    KnowledgePointPreviewItem,
    build_knowledge_point_preview_items,
    create_selections_from_preview_choice,
)

__all__ = [
    "AIProviderError",
    "AIProviderMetadata",
    "AIProviderResult",
    "AIKnowledgePointExtractor",
    "CardCandidate",
    "CardCandidatePreviewItem",
    "HumanReview",
    "HumanSelection",
    "FakeAIProvider",
    "KnowledgePoint",
    "KnowledgePointExtractionOutcome",
    "KnowledgePointExtractionRequest",
    "KnowledgePointExtractionResponse",
    "KnowledgePointJSONProvider",
    "KnowledgePointPreviewItem",
    "MockKnowledgePointExtractor",
    "OpenAICompatibleKnowledgePointProvider",
    "OpenAICompatibleProviderConfig",
    "OpenAICompatibleTransport",
    "OpenAICompatibleTransportResponse",
    "PipelineRunResult",
    "PipelineRunStatus",
    "PipelineRunSummary",
    "PipelineRunWithStatus",
    "PipelineWriteEligibility",
    "QualityGateResult",
    "QualityIssue",
    "QualityIssuePreviewItem",
    "QualityReviewPreviewState",
    "ReadOnlyCardPreviewItem",
    "ReadOnlyPipelinePreviewData",
    "SafeKnowledgePointJSONProvider",
    "SourceChunk",
    "SourceDocument",
    "WriteReadyPreviewItem",
    "build_candidate_id",
    "build_chat_completions_payload",
    "build_chat_completions_url",
    "build_card_candidate_preview_item",
    "build_card_candidate_preview_items",
    "build_quality_review_preview_state",
    "build_knowledge_point_preview_items",
    "build_knowledge_point_extraction_request",
    "build_pipeline_write_eligibility",
    "build_read_only_pipeline_preview",
    "build_review_id",
    "build_selection_id",
    "build_write_ready_preview_item",
    "build_write_ready_preview_items",
    "build_knowledge_point_id",
    "create_card_candidate",
    "create_card_candidates",
    "create_human_review",
    "create_human_reviews",
    "create_human_selection",
    "create_human_selections",
    "create_selections_from_preview_choice",
    "extract_mock_knowledge_points",
    "extract_knowledge_points",
    "extract_ai_knowledge_points_from_chunks",
    "extract_knowledge_points_from_chunks",
    "parse_knowledge_points_json",
    "parse_knowledge_points_payload",
    "run_quality_gate",
    "run_quality_gate_for_candidates",
    "run_full_mock_pipeline",
    "run_full_mock_pipeline_with_status",
    "summarize_pipeline_run",
    "validate_quality_issue",
]

