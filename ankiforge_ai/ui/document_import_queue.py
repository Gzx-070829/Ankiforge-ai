"""Immutable, path-private state for explicit local document imports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

from ..document import DEFAULT_DOCUMENT_LIMITS, DocumentIR, get_safe_source_label
from ..intelligence import DocumentAnalysis, DocumentChunk, PlanEstimate


_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,119}$")
_SAFE_ITEM_ID = re.compile(r"^item-[1-9][0-9]*$")
_MAX_WARNING_CODES = 32


class DocumentImportStatus(str, Enum):
    QUEUED = "queued"
    IMPORTING = "importing"
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"


@dataclass(frozen=True, repr=False)
class PrivatePathToken:
    """A selected local path whose public renderings expose only its basename."""

    _path_token: str = field(repr=False)
    filename: str
    byte_size: int

    def __post_init__(self) -> None:
        if not isinstance(self._path_token, str) or not self._path_token:
            raise ValueError("selected path token must be a non-empty string")
        if self.filename != get_safe_source_label(self._path_token):
            raise ValueError("filename must match the safe selected-path label")
        if (
            isinstance(self.byte_size, bool)
            or not isinstance(self.byte_size, int)
            or self.byte_size < 0
        ):
            raise ValueError("byte_size must be a non-negative integer")

    @classmethod
    def from_path(cls, path, *, byte_size: int) -> "PrivatePathToken":
        value = str(path)
        return cls(
            _path_token=value,
            filename=get_safe_source_label(value),
            byte_size=byte_size,
        )

    def as_path(self) -> Path:
        """Return the private worker value; callers must not log or persist it."""

        return Path(self._path_token)

    def to_safe_dict(self) -> dict[str, object]:
        return {"filename": self.filename, "byte_size": self.byte_size}

    def __repr__(self) -> str:
        return (
            "PrivatePathToken("
            f"filename={self.filename!r}, byte_size={self.byte_size})"
        )


@dataclass(frozen=True, repr=False)
class DocumentImportRequestSnapshot:
    request_id: int
    item_id: str
    path_token: PrivatePathToken = field(repr=False)

    def __post_init__(self) -> None:
        _validate_request_id(self.request_id)
        _validate_item_id(self.item_id)
        if not isinstance(self.path_token, PrivatePathToken):
            raise TypeError("path_token must be a PrivatePathToken")

    def __repr__(self) -> str:
        return (
            "DocumentImportRequestSnapshot("
            f"request_id={self.request_id}, item_id={self.item_id!r}, "
            f"filename={self.path_token.filename!r})"
        )


@dataclass(frozen=True, repr=False)
class DocumentImportWorkerResult:
    document: DocumentIR = field(repr=False)
    file_type: str
    importer_name: str
    warning_codes: tuple[str, ...] = ()
    analysis: Optional[DocumentAnalysis] = field(default=None, repr=False)
    chunks: tuple[DocumentChunk, ...] = field(default=(), repr=False)
    estimates: tuple[PlanEstimate, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.document, DocumentIR):
            raise TypeError("document must be a DocumentIR")
        for name in ("file_type", "importer_name"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or len(value) > 120:
                raise ValueError(f"{name} must be a bounded non-empty string")
        warnings = _validate_warning_codes(self.warning_codes)
        if self.analysis is not None and not isinstance(
            self.analysis,
            DocumentAnalysis,
        ):
            raise TypeError("analysis must be a DocumentAnalysis or None")
        chunks = tuple(self.chunks)
        estimates = tuple(self.estimates)
        if not all(isinstance(chunk, DocumentChunk) for chunk in chunks):
            raise TypeError("chunks must contain DocumentChunk values")
        if not all(isinstance(estimate, PlanEstimate) for estimate in estimates):
            raise TypeError("estimates must contain PlanEstimate values")
        if self.analysis is None and (chunks or estimates):
            raise ValueError("analysis is required with chunks or estimates")
        if self.analysis is not None:
            if self.analysis.document_id != self.document.document_id:
                raise ValueError("analysis does not match the document")
            if any(
                chunk.document_id != self.document.document_id
                for chunk in chunks
            ):
                raise ValueError("chunks do not match the document")
        if estimates and tuple(estimate.level.value for estimate in estimates) != (
            "fast",
            "standard",
            "deep",
        ):
            raise ValueError("estimates must contain fast, standard, and deep")
        object.__setattr__(self, "warning_codes", warnings)
        object.__setattr__(self, "chunks", chunks)
        object.__setattr__(self, "estimates", estimates)

    def __repr__(self) -> str:
        return (
            "DocumentImportWorkerResult("
            f"file_type={self.file_type!r}, importer_name={self.importer_name!r}, "
            f"sections={len(self.document.sections)}, "
            f"chars={self.document.extracted_char_count}, "
            f"chunks={len(self.chunks)}, "
            f"warnings={self.warning_codes!r})"
        )


@dataclass(frozen=True, repr=False)
class DocumentImportTaskCompletion:
    request_id: int
    item_id: str
    result: Optional[DocumentImportWorkerResult] = field(
        default=None,
        repr=False,
    )
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_request_id(self.request_id)
        _validate_item_id(self.item_id)
        if self.result is not None and not isinstance(
            self.result,
            DocumentImportWorkerResult,
        ):
            raise TypeError("result must be a DocumentImportWorkerResult")
        if self.error_code is not None:
            _validate_code(self.error_code, "error_code")
        if (self.result is None) == (self.error_code is None):
            raise ValueError("completion requires exactly one result or error_code")

    def __repr__(self) -> str:
        return (
            "DocumentImportTaskCompletion("
            f"request_id={self.request_id}, item_id={self.item_id!r}, "
            f"has_result={self.result is not None}, "
            f"error_code={self.error_code!r})"
        )


@dataclass(frozen=True)
class DocumentImportRow:
    filename: str
    file_type: str
    importer: str
    status: DocumentImportStatus
    section_count: int
    block_count: int
    char_count: int
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.filename != get_safe_source_label(self.filename):
            raise ValueError("filename must be a safe source label")
        for name in ("file_type", "importer"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) > 120:
                raise ValueError(f"{name} must be a bounded string")
        try:
            status = DocumentImportStatus(self.status)
        except (TypeError, ValueError):
            raise ValueError("status is unsupported") from None
        for value in (self.section_count, self.block_count, self.char_count):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError("row counts must be non-negative integers")
        warnings = _validate_warning_codes(self.warnings)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "warnings", warnings)

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "file_type": self.file_type,
            "importer": self.importer,
            "status": self.status.value,
            "section_count": self.section_count,
            "block_count": self.block_count,
            "char_count": self.char_count,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, repr=False)
class _DocumentImportItem:
    item_id: str
    path_token: PrivatePathToken = field(repr=False)
    status: DocumentImportStatus = DocumentImportStatus.QUEUED
    request_id: Optional[int] = None
    document: Optional[DocumentIR] = field(default=None, repr=False)
    worker_result: Optional[DocumentImportWorkerResult] = field(
        default=None,
        repr=False,
    )
    file_type: str = ""
    importer_name: str = ""
    warning_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_item_id(self.item_id)
        if not isinstance(self.path_token, PrivatePathToken):
            raise TypeError("path_token must be a PrivatePathToken")
        try:
            status = DocumentImportStatus(self.status)
        except (TypeError, ValueError):
            raise ValueError("status is unsupported") from None
        if self.request_id is not None:
            _validate_request_id(self.request_id)
        if self.document is not None and not isinstance(self.document, DocumentIR):
            raise TypeError("document must be a DocumentIR")
        if self.worker_result is not None and not isinstance(
            self.worker_result,
            DocumentImportWorkerResult,
        ):
            raise TypeError("worker_result must be a DocumentImportWorkerResult")
        warnings = _validate_warning_codes(self.warning_codes)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "warning_codes", warnings)


@dataclass(frozen=True, repr=False)
class DocumentImportQueue:
    _items: tuple[_DocumentImportItem, ...] = field(default=(), repr=False)
    _next_item_number: int = 1
    _next_request_id: int = 1

    def __post_init__(self) -> None:
        items = tuple(self._items)
        if len(items) > DEFAULT_DOCUMENT_LIMITS.max_files_per_batch:
            raise ValueError("too_many_files")
        if not all(isinstance(item, _DocumentImportItem) for item in items):
            raise TypeError("queue items are invalid")
        if len({item.item_id for item in items}) != len(items):
            raise ValueError("queue item IDs must be unique")
        if sum(item.path_token.byte_size for item in items) > (
            DEFAULT_DOCUMENT_LIMITS.max_total_batch_bytes
        ):
            raise ValueError("batch_too_large")
        for value, name in (
            (self._next_item_number, "next item number"),
            (self._next_request_id, "next request ID"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        object.__setattr__(self, "_items", items)

    @property
    def total_bytes(self) -> int:
        return sum(item.path_token.byte_size for item in self._items)

    @property
    def safe_rows(self) -> tuple[DocumentImportRow, ...]:
        rows = []
        for item in self._items:
            document = item.document
            rows.append(
                DocumentImportRow(
                    filename=item.path_token.filename,
                    file_type=item.file_type,
                    importer=item.importer_name,
                    status=item.status,
                    section_count=0 if document is None else len(document.sections),
                    block_count=(
                        0
                        if document is None
                        else sum(len(section.blocks) for section in document.sections)
                    ),
                    char_count=(
                        0 if document is None else document.extracted_char_count
                    ),
                    warnings=item.warning_codes,
                )
            )
        return tuple(rows)

    @property
    def successful_documents(self) -> tuple[DocumentIR, ...]:
        return tuple(
            item.document
            for item in self._items
            if item.status
            in {DocumentImportStatus.SUCCESS, DocumentImportStatus.WARNING}
            and item.document is not None
        )

    @property
    def successful_results(self) -> tuple[DocumentImportWorkerResult, ...]:
        return tuple(
            item.worker_result
            for item in self._items
            if item.status
            in {DocumentImportStatus.SUCCESS, DocumentImportStatus.WARNING}
            and item.worker_result is not None
        )

    @property
    def imports_pending(self) -> bool:
        return any(
            item.status
            in {
                DocumentImportStatus.QUEUED,
                DocumentImportStatus.IMPORTING,
            }
            for item in self._items
        )

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "rows": [row.to_safe_dict() for row in self.safe_rows],
            "total_bytes": self.total_bytes,
        }

    def __repr__(self) -> str:
        statuses = tuple(row.status.value for row in self.safe_rows)
        return (
            "DocumentImportQueue("
            f"files={len(self._items)}, total_bytes={self.total_bytes}, "
            f"statuses={statuses!r})"
        )


def create_import_queue(
    path_tokens: Iterable[PrivatePathToken] = (),
) -> DocumentImportQueue:
    return add_import_paths(DocumentImportQueue(), path_tokens)


def add_import_paths(
    queue: DocumentImportQueue,
    path_tokens: Iterable[PrivatePathToken],
) -> DocumentImportQueue:
    _require_queue(queue)
    tokens = _bounded_tokens(path_tokens)
    if len(queue._items) + len(tokens) > DEFAULT_DOCUMENT_LIMITS.max_files_per_batch:
        raise ValueError("too_many_files")
    if queue.total_bytes + sum(token.byte_size for token in tokens) > (
        DEFAULT_DOCUMENT_LIMITS.max_total_batch_bytes
    ):
        raise ValueError("batch_too_large")
    new_items = tuple(
        _DocumentImportItem(
            item_id=f"item-{queue._next_item_number + offset}",
            path_token=token,
        )
        for offset, token in enumerate(tokens)
    )
    return replace(
        queue,
        _items=queue._items + new_items,
        _next_item_number=queue._next_item_number + len(new_items),
    )


def remove_import_item(
    queue: DocumentImportQueue,
    index: int,
) -> DocumentImportQueue:
    _require_queue(queue)
    _validate_index(index, len(queue._items))
    return replace(queue, _items=queue._items[:index] + queue._items[index + 1 :])


def move_import_item(
    queue: DocumentImportQueue,
    source_index: int,
    destination_index: int,
) -> DocumentImportQueue:
    _require_queue(queue)
    _validate_index(source_index, len(queue._items))
    _validate_index(destination_index, len(queue._items))
    items = list(queue._items)
    item = items.pop(source_index)
    items.insert(destination_index, item)
    return replace(queue, _items=tuple(items))


def begin_import(
    queue: DocumentImportQueue,
    index: int,
) -> tuple[DocumentImportQueue, DocumentImportRequestSnapshot]:
    _require_queue(queue)
    _validate_index(index, len(queue._items))
    item = queue._items[index]
    if item.status not in {
        DocumentImportStatus.QUEUED,
        DocumentImportStatus.FAILURE,
    }:
        raise ValueError("only queued or failed items can start importing")
    request_id = queue._next_request_id
    updated = replace(
        item,
        status=DocumentImportStatus.IMPORTING,
        request_id=request_id,
        document=None,
        worker_result=None,
        file_type="",
        importer_name="",
        warning_codes=(),
    )
    items = queue._items[:index] + (updated,) + queue._items[index + 1 :]
    request = DocumentImportRequestSnapshot(
        request_id=request_id,
        item_id=item.item_id,
        path_token=item.path_token,
    )
    return (
        replace(
            queue,
            _items=items,
            _next_request_id=request_id + 1,
        ),
        request,
    )


def apply_import_completion(
    queue: DocumentImportQueue,
    completion: DocumentImportTaskCompletion,
) -> DocumentImportQueue:
    _require_queue(queue)
    if not isinstance(completion, DocumentImportTaskCompletion):
        raise TypeError("completion must be a DocumentImportTaskCompletion")
    index = next(
        (
            position
            for position, item in enumerate(queue._items)
            if item.item_id == completion.item_id
        ),
        None,
    )
    if index is None:
        return queue
    item = queue._items[index]
    if (
        item.status is not DocumentImportStatus.IMPORTING
        or item.request_id != completion.request_id
    ):
        return queue
    if completion.result is None:
        updated = replace(
            item,
            status=DocumentImportStatus.FAILURE,
            worker_result=None,
            warning_codes=(completion.error_code,),
        )
    else:
        result = completion.result
        document_warnings = tuple(warning.code for warning in result.document.warnings)
        warning_codes = tuple(
            dict.fromkeys(result.warning_codes + document_warnings)
        )
        updated = replace(
            item,
            status=(
                DocumentImportStatus.WARNING
                if warning_codes
                else DocumentImportStatus.SUCCESS
            ),
            document=result.document,
            worker_result=result,
            file_type=result.file_type,
            importer_name=result.importer_name,
            warning_codes=warning_codes,
        )
    return replace(
        queue,
        _items=queue._items[:index] + (updated,) + queue._items[index + 1 :],
    )


def retry_failed_imports(
    queue: DocumentImportQueue,
) -> tuple[DocumentImportQueue, tuple[DocumentImportRequestSnapshot, ...]]:
    _require_queue(queue)
    current = queue
    requests = []
    failed_item_ids = tuple(
        item.item_id
        for item in queue._items
        if item.status is DocumentImportStatus.FAILURE
    )
    for item_id in failed_item_ids:
        index = next(
            position
            for position, item in enumerate(current._items)
            if item.item_id == item_id
        )
        current, request = begin_import(current, index)
        requests.append(request)
    return current, tuple(requests)


def _bounded_tokens(
    path_tokens: Iterable[PrivatePathToken],
) -> tuple[PrivatePathToken, ...]:
    if isinstance(path_tokens, (str, bytes)):
        raise TypeError("path_tokens must be an iterable of PrivatePathToken")
    iterator = iter(path_tokens)
    tokens = []
    for _index in range(DEFAULT_DOCUMENT_LIMITS.max_files_per_batch + 1):
        try:
            tokens.append(next(iterator))
        except StopIteration:
            break
    if len(tokens) > DEFAULT_DOCUMENT_LIMITS.max_files_per_batch:
        raise ValueError("too_many_files")
    if not all(isinstance(token, PrivatePathToken) for token in tokens):
        raise TypeError("path_tokens must contain PrivatePathToken values")
    return tuple(tokens)


def _validate_warning_codes(values) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError("warning_codes must be a sequence")
    result = tuple(values)
    if len(result) > _MAX_WARNING_CODES:
        raise ValueError("warning_codes exceed the approved limit")
    for value in result:
        _validate_code(value, "warning code")
    return result


def _validate_code(value: object, name: str) -> None:
    if not isinstance(value, str) or not _SAFE_CODE.fullmatch(value):
        raise ValueError(f"{name} must be a safe code")


def _validate_request_id(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("request_id must be a positive integer")


def _validate_item_id(value: object) -> None:
    if not isinstance(value, str) or not _SAFE_ITEM_ID.fullmatch(value):
        raise ValueError("item_id must be a safe queue identifier")


def _validate_index(index: object, length: int) -> None:
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("queue index must be an integer")
    if not 0 <= index < length:
        raise IndexError("queue index is out of range")


def _require_queue(queue: object) -> None:
    if not isinstance(queue, DocumentImportQueue):
        raise TypeError("queue must be a DocumentImportQueue")


__all__ = [
    "DocumentImportQueue",
    "DocumentImportRequestSnapshot",
    "DocumentImportRow",
    "DocumentImportStatus",
    "DocumentImportTaskCompletion",
    "DocumentImportWorkerResult",
    "PrivatePathToken",
    "add_import_paths",
    "apply_import_completion",
    "begin_import",
    "create_import_queue",
    "move_import_item",
    "remove_import_item",
    "retry_failed_imports",
]
