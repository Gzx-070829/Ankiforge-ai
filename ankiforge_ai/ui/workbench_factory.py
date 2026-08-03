"""UI composition root for workbench application services."""

from __future__ import annotations

from ..anki_writer.minimal_write import MinimalAnkiWriter
from ..workbench.write_coordinator import WorkbenchWriteCoordinator
from .beginner_final_confirmation import (
    build_beginner_final_confirmation_preview,
)
from .beginner_real_write import (
    execute_beginner_write_if_confirmed,
    prepare_beginner_write,
)
from .read_only_anki_targets import ReadOnlyAnkiTargetAdapter
from .read_only_duplicate_check import ReadOnlyDuplicateCheckAdapter


def create_workbench_write_coordinator(collection):
    """Inject the existing audited Anki boundaries into one coordinator."""

    return WorkbenchWriteCoordinator(
        target_adapter=ReadOnlyAnkiTargetAdapter(collection),
        duplicate_adapter=ReadOnlyDuplicateCheckAdapter(collection),
        writer=MinimalAnkiWriter(collection),
        final_preview_builder=build_beginner_final_confirmation_preview,
        write_preparer=prepare_beginner_write,
        confirmed_executor=execute_beginner_write_if_confirmed,
    )


__all__ = ["create_workbench_write_coordinator"]
