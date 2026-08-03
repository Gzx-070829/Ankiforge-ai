"""Pure application state and use cases for the AnkiForge AI workbench."""

from .models import (
    GenerationState,
    MaterialState,
    ReviewDecisionRecord,
    ReviewState,
    WorkbenchArtifactStatus,
    WorkbenchSessionState,
    WriteState,
    initial_workbench_state,
)
from .transitions import (
    change_mapping,
    change_target,
    close_session,
    complete_generation,
    fail_generation,
    mark_duplicate_check_current,
    record_review_decision,
    start_generation,
    update_material,
    write_is_ready,
)
from .legacy_bridge import project_legacy_session
from .store import WorkbenchSessionStore
from .generation_lifecycle import (
    GenerationLifecycleResult,
    IntelligentGenerationProgress,
    apply_coverage_supplement,
    execute_failed_retry_lifecycle,
    execute_generation_lifecycle,
    failed_generation_retry_is_available,
)
from .review_use_cases import (
    MAX_REVIEW_CARD_TEXT_CHARS,
    ReviewSessionPort,
    ReviewUseCases,
)


__all__ = [
    "GenerationState",
    "GenerationLifecycleResult",
    "IntelligentGenerationProgress",
    "MAX_REVIEW_CARD_TEXT_CHARS",
    "MaterialState",
    "ReviewDecisionRecord",
    "ReviewSessionPort",
    "ReviewState",
    "ReviewUseCases",
    "WorkbenchArtifactStatus",
    "WorkbenchSessionState",
    "WorkbenchSessionStore",
    "WriteState",
    "apply_coverage_supplement",
    "change_mapping",
    "change_target",
    "close_session",
    "complete_generation",
    "fail_generation",
    "execute_failed_retry_lifecycle",
    "execute_generation_lifecycle",
    "failed_generation_retry_is_available",
    "initial_workbench_state",
    "mark_duplicate_check_current",
    "project_legacy_session",
    "record_review_decision",
    "start_generation",
    "update_material",
    "write_is_ready",
]
