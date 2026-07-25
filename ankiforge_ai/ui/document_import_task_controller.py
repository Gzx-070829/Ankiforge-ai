"""Async adapter for explicit local document imports without collection access."""

from __future__ import annotations

from typing import Callable, Iterable, Optional

from ..document import (
    DEFAULT_DOCUMENT_LIMITS,
    DocumentImportError,
    create_native_importer_registry,
    detect_file_type,
    document_to_plain_text,
)
from ..intelligence import (
    IntelligenceLevel,
    analyze_document,
    chunk_document,
    estimate_generation,
)
from .document_import_queue import (
    DocumentImportRequestSnapshot,
    DocumentImportTaskCompletion,
    DocumentImportWorkerResult,
)


class DocumentImportTaskController:
    """Run one current request while safely discarding stale completions."""

    def __init__(self, taskman):
        run_in_background = getattr(taskman, "run_in_background", None)
        if not callable(run_in_background):
            raise TypeError("taskman must provide run_in_background")
        self._taskman = taskman
        self._current_request_id: Optional[int] = None
        self._running = False
        self._alive = True

    @property
    def current_request_id(self) -> Optional[int]:
        return self._current_request_id

    @property
    def running(self) -> bool:
        return self._running

    @property
    def alive(self) -> bool:
        return self._alive

    def submit(
        self,
        *,
        request: DocumentImportRequestSnapshot,
        importer_callback: Callable[
            [object],
            DocumentImportWorkerResult,
        ],
        on_complete: Callable[[DocumentImportTaskCompletion], None],
    ) -> Optional[int]:
        if not self._alive:
            return None
        if not isinstance(request, DocumentImportRequestSnapshot):
            raise TypeError("request must be a DocumentImportRequestSnapshot")
        if not callable(importer_callback):
            raise TypeError("importer_callback must be callable")
        if not callable(on_complete):
            raise TypeError("on_complete must be callable")

        self._current_request_id = request.request_id
        self._running = True

        def background_task():
            result = importer_callback(request.path_token)
            if not isinstance(result, DocumentImportWorkerResult):
                raise TypeError("importer callback returned an invalid result")
            return result

        def on_done(future):
            try:
                result = future.result()
                completion = DocumentImportTaskCompletion(
                    request_id=request.request_id,
                    item_id=request.item_id,
                    result=result,
                )
            except DocumentImportError as exc:
                completion = DocumentImportTaskCompletion(
                    request_id=request.request_id,
                    item_id=request.item_id,
                    error_code=exc.code,
                )
            except Exception:
                completion = DocumentImportTaskCompletion(
                    request_id=request.request_id,
                    item_id=request.item_id,
                    error_code="document_import_failed",
                )
            self._finish_if_current(completion, on_complete)

        try:
            self._taskman.run_in_background(
                background_task,
                on_done,
                uses_collection=False,
            )
        except Exception:
            self._finish_if_current(
                DocumentImportTaskCompletion(
                    request_id=request.request_id,
                    item_id=request.item_id,
                    error_code="document_import_submit_failed",
                ),
                on_complete,
            )
        return request.request_id

    def invalidate(self) -> None:
        self._current_request_id = None
        self._running = False

    def close(self) -> None:
        self._alive = False
        self.invalidate()

    def _finish_if_current(
        self,
        completion: DocumentImportTaskCompletion,
        on_complete: Callable[[DocumentImportTaskCompletion], None],
    ) -> None:
        if (
            not self._alive
            or completion.request_id != self._current_request_id
        ):
            return
        self._current_request_id = None
        self._running = False
        try:
            on_complete(completion)
        except Exception:
            return


def import_document_path_token(path_token) -> DocumentImportWorkerResult:
    """Parse and analyze one explicitly selected local token off the Qt thread."""

    from .document_import_queue import PrivatePathToken

    if not isinstance(path_token, PrivatePathToken):
        raise TypeError("path_token must be a PrivatePathToken")
    path = path_token.as_path()
    detected = detect_file_type(path, DEFAULT_DOCUMENT_LIMITS)
    registry = create_native_importer_registry()
    importer = registry.select_importer(path, DEFAULT_DOCUMENT_LIMITS)
    document = importer.import_document(path, DEFAULT_DOCUMENT_LIMITS)
    analysis = analyze_document(document)
    chunks = chunk_document(document)
    estimates = tuple(
        estimate_generation(analysis, chunks, level=level)
        for level in IntelligenceLevel
    )
    return DocumentImportWorkerResult(
        document=document,
        file_type=detected.file_type,
        importer_name=importer.importer_id.upper(),
        warning_codes=detected.warnings,
        analysis=analysis,
        chunks=chunks,
        estimates=estimates,
    )


def build_bounded_import_material(
    results: Iterable[DocumentImportWorkerResult],
    *,
    max_chars: int,
) -> str:
    """Render every successful document in queue order within an explicit cap."""

    if (
        isinstance(max_chars, bool)
        or not isinstance(max_chars, int)
        or max_chars < 1
    ):
        raise ValueError("max_chars must be a positive integer")
    selected = tuple(results)
    if not all(isinstance(item, DocumentImportWorkerResult) for item in selected):
        raise TypeError("results must contain DocumentImportWorkerResult values")
    parts = tuple(
        f"# {item.document.source_label}\n{document_to_plain_text(item.document)}"
        for item in selected
    )
    return "\n\n".join(parts)[:max_chars]


__all__ = [
    "DocumentImportTaskController",
    "build_bounded_import_material",
    "import_document_path_token",
]
