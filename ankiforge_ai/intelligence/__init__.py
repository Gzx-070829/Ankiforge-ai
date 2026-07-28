"""Deterministic document-intelligence foundation."""

from .analyzer import analyze_document
from .call_budget import (
    MAX_AI_CALLS_PER_RUN,
    CallBudget,
    CallBudgetError,
    CallPurpose,
    CallReservation,
)
from .chunking import DocumentChunk, chunk_document
from .coverage import CoverageReport, assess_generation_coverage
from .critic import (
    CriticAction,
    CriticDecision,
    RepairResult,
    decide_card,
    repair_and_revalidate,
)
from .deck_style import (
    DEFAULT_DECK_STYLE_MAX_NOTES,
    REAL_DECK_STYLE_SAMPLING_ENABLED,
    DeckStyleProfile,
    DeckStyleQuery,
    build_deck_style_query,
    summarize_deck_style,
)
from .deduplication import (
    DeduplicationResult,
    canonicalize_card_text,
    deduplicate_cards,
)
from .estimates import estimate_generation
from .generation_run import (
    ChunkGenerationSnapshot,
    ChunkGenerationState,
    GenerationRun,
    GenerationRunStatus,
    GenerationStage,
    complete_run,
    create_generation_run,
    fail_chunk,
    reserve_run_call,
    start_chunk,
    succeed_chunk,
    supersede_run,
    transition_run,
)
from .models import (
    DocumentAnalysis,
    IntelligenceLevel,
    PlanEstimate,
    TemplateRoute,
)
from .recovery import (
    FailedChunkRetry,
    apply_failed_chunk_retry,
    create_failed_chunk_retry,
    fail_failed_chunk_retry,
    start_failed_chunk_retry,
    succeed_failed_chunk_retry,
)
from .template_router import route_template
from .planning import (
    KnowledgePlan,
    KnowledgePointPlan,
    PlanCoverage,
    assess_plan_coverage,
    build_local_knowledge_plan,
    parse_llm_knowledge_plan,
)

__all__ = [
    "CallBudget",
    "CallBudgetError",
    "CallPurpose",
    "CallReservation",
    "ChunkGenerationSnapshot",
    "ChunkGenerationState",
    "CoverageReport",
    "CriticAction",
    "CriticDecision",
    "DEFAULT_DECK_STYLE_MAX_NOTES",
    "DeckStyleProfile",
    "DeckStyleQuery",
    "DeduplicationResult",
    "DocumentAnalysis",
    "DocumentChunk",
    "FailedChunkRetry",
    "GenerationRun",
    "GenerationRunStatus",
    "GenerationStage",
    "IntelligenceLevel",
    "KnowledgePlan",
    "KnowledgePointPlan",
    "MAX_AI_CALLS_PER_RUN",
    "PlanEstimate",
    "PlanCoverage",
    "REAL_DECK_STYLE_SAMPLING_ENABLED",
    "RepairResult",
    "TemplateRoute",
    "analyze_document",
    "apply_failed_chunk_retry",
    "assess_generation_coverage",
    "assess_plan_coverage",
    "build_deck_style_query",
    "build_local_knowledge_plan",
    "canonicalize_card_text",
    "chunk_document",
    "complete_run",
    "create_failed_chunk_retry",
    "create_generation_run",
    "decide_card",
    "deduplicate_cards",
    "estimate_generation",
    "fail_chunk",
    "fail_failed_chunk_retry",
    "parse_llm_knowledge_plan",
    "repair_and_revalidate",
    "reserve_run_call",
    "route_template",
    "start_chunk",
    "start_failed_chunk_retry",
    "succeed_chunk",
    "succeed_failed_chunk_retry",
    "summarize_deck_style",
    "supersede_run",
    "transition_run",
]
