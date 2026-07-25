"""Async adapter for explicit local document imports without collection access."""

from __future__ import annotations

from dataclasses import dataclass
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


def import_document_path_token(
    path_token,
    *,
    enabled_backend_ids=(),
    pandoc_executable=None,
) -> DocumentImportWorkerResult:
    """Parse and analyze one explicitly selected local token off the Qt thread."""

    from .document_import_queue import PrivatePathToken

    if not isinstance(path_token, PrivatePathToken):
        raise TypeError("path_token must be a PrivatePathToken")
    enabled = _validated_backend_ids(enabled_backend_ids)
    path = path_token.as_path()
    detected = detect_file_type(path, DEFAULT_DOCUMENT_LIMITS)
    registry = create_native_importer_registry()
    importer = _selected_optional_importer(
        path,
        detected.extension,
        enabled,
        pandoc_executable=pandoc_executable,
    )
    if importer is None:
        try:
            importer = registry.select_importer(
                path,
                DEFAULT_DOCUMENT_LIMITS,
            )
        except DocumentImportError as exc:
            if exc.code == "unsupported_type" and detected.file_type == "pdf":
                raise _optional_backend_missing() from None
            raise
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


def _validated_backend_ids(values) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError("enabled_backend_ids must be a sequence")
    enabled = tuple(values)
    if (
        len(enabled) > 3
        or len(set(enabled)) != len(enabled)
        or not all(
            value in {"docling", "markitdown", "pandoc"}
            for value in enabled
        )
    ):
        raise ValueError("enabled_backend_ids contains an unsupported backend")
    return enabled


def _selected_optional_importer(
    path,
    detected_extension,
    enabled_backend_ids,
    *,
    pandoc_executable,
):
    if not enabled_backend_ids:
        return None
    from ..document.importers.optional_backends import (
        create_optional_backend_importers,
    )

    importers = create_optional_backend_importers(
        enabled_backend_ids,
        pandoc_executable=pandoc_executable,
    )
    for importer in importers:
        if detected_extension not in importer.supported_extensions:
            continue
        try:
            available = importer.availability()
        except Exception:
            raise _optional_backend_missing() from None
        if not available:
            raise _optional_backend_missing()
        return importer
    return None


def _optional_backend_missing() -> DocumentImportError:
    return DocumentImportError(
        code="optional_backend_missing",
        message_key="document.error.optional_backend_missing",
        action_key="document.action.configure_backend_or_copy_text",
    )


@dataclass(frozen=True)
class BoundedImportMaterialPreview:
    text: str
    truncated: bool
    original_char_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("text must be a string")
        if not isinstance(self.truncated, bool):
            raise TypeError("truncated must be a boolean")
        if (
            isinstance(self.original_char_count, bool)
            or not isinstance(self.original_char_count, int)
            or self.original_char_count < len(self.text)
        ):
            raise ValueError("original_char_count must cover the preview")


def build_bounded_import_material_preview(
    results: Iterable[DocumentImportWorkerResult],
    *,
    max_chars: int,
) -> BoundedImportMaterialPreview:
    """Render an explicitly labelled preview; generation keeps full documents."""

    if (
        isinstance(max_chars, bool)
        or not isinstance(max_chars, int)
        or max_chars < 1
    ):
        raise ValueError("max_chars must be a positive integer")
    material = _full_import_material(results)
    return BoundedImportMaterialPreview(
        text=material[:max_chars],
        truncated=len(material) > max_chars,
        original_char_count=len(material),
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
    return build_bounded_import_material_preview(
        results,
        max_chars=max_chars,
    ).text


def _full_import_material(
    results: Iterable[DocumentImportWorkerResult],
) -> str:
    selected = tuple(results)
    if not all(isinstance(item, DocumentImportWorkerResult) for item in selected):
        raise TypeError("results must contain DocumentImportWorkerResult values")
    return "\n\n".join(
        f"# {item.document.source_label}\n{document_to_plain_text(item.document)}"
        for item in selected
    )


__all__ = [
    "DocumentImportTaskController",
    "BoundedImportMaterialPreview",
    "build_bounded_import_material",
    "build_bounded_import_material_preview",
    "import_document_path_token",
]
