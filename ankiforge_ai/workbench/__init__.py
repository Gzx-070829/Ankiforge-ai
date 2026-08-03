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


__all__ = [
    "GenerationState",
    "MaterialState",
    "ReviewDecisionRecord",
    "ReviewState",
    "WorkbenchArtifactStatus",
    "WorkbenchSessionState",
    "WorkbenchSessionStore",
    "WriteState",
    "change_mapping",
    "change_target",
    "close_session",
    "complete_generation",
    "fail_generation",
    "initial_workbench_state",
    "mark_duplicate_check_current",
    "project_legacy_session",
    "record_review_decision",
    "start_generation",
    "update_material",
    "write_is_ready",
]
