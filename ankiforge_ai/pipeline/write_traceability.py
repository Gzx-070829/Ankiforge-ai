"""Safe source labels, tags, write summaries, and last-batch tracking."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Iterable
import uuid

from .generation_settings import GenerationSettings, coerce_generation_settings


MAX_TAG_LENGTH = 48
_SECRET_MARKER = re.compile(
    r"(?:\b(?:bearer|password|authorization)\b|sk-[a-z0-9_-]{8,})",
    re.IGNORECASE,
)
_WINDOWS_PATH = re.compile(r"^[a-zA-Z]:[\\/]")
_TRACE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class SourceType(str, Enum):
    PASTE = "paste"
    MARKDOWN = "markdown"
    TXT = "txt"
    DOCX = "docx"
    PDF_FALLBACK = "pdf-fallback"
    UNKNOWN = "unknown"


_SOURCE_LABELS = {
    SourceType.PASTE: {"zh": "粘贴文本", "en": "Pasted text"},
    SourceType.MARKDOWN: {"zh": "Markdown 导入", "en": "Markdown import"},
    SourceType.TXT: {"zh": "TXT 导入", "en": "TXT import"},
    SourceType.DOCX: {"zh": "DOCX 导入", "en": "Imported from DOCX"},
    SourceType.PDF_FALLBACK: {"zh": "PDF fallback", "en": "PDF fallback"},
    SourceType.UNKNOWN: {"zh": "导入材料", "en": "Imported material"},
}


def coerce_source_type(value: SourceType | str) -> SourceType:
    if isinstance(value, SourceType):
        return value
    try:
        return SourceType(value)
    except (ValueError, TypeError):
        return SourceType.UNKNOWN


def source_type_from_path(path: object) -> SourceType:
    text = str(path).strip().casefold() if path is not None else ""
    suffix = "." + text.rsplit(".", 1)[-1] if "." in text else ""
    if suffix in {".md", ".markdown"}:
        return SourceType.MARKDOWN
    if suffix == ".txt":
        return SourceType.TXT
    if suffix == ".docx":
        return SourceType.DOCX
    if suffix == ".pdf":
        return SourceType.PDF_FALLBACK
    return SourceType.UNKNOWN


def safe_source_label(
    source_type: SourceType | str,
    language: str = "en",
) -> str:
    if language not in {"zh", "en"}:
        raise ValueError("language must be zh or en.")
    return _SOURCE_LABELS[coerce_source_type(source_type)][language]


def normalize_tag(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().casefold().replace("_", "-")
    normalized = re.sub(r"[^a-z0-9-]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized[:MAX_TAG_LENGTH].rstrip("-")


def build_default_tags(
    settings: GenerationSettings | None,
    source_type: SourceType | str,
) -> tuple[str, ...]:
    resolved = coerce_generation_settings(settings)
    source = coerce_source_type(source_type)
    return _normalized_tags(
        (
            "ankiforge",
            "ankiforge-ai",
            f"mode-{resolved.card_mode.replace('_', '-')}",
            f"source-{source.value}",
        )
    )


def validate_tags(tags: tuple[str, ...], *, allow_empty: bool = False) -> None:
    if allow_empty and tags == ():
        return
    _validate_tags(tags)


@dataclass(frozen=True, repr=False)
class WriteSummary:
    target_deck: str = field(repr=False)
    note_type: str = field(repr=False)
    field_mapping: tuple[str, ...] = field(repr=False)
    source_label: str = field(repr=False)
    cards_to_write: int
    warning_count: int
    blocking_count: int
    duplicate_behavior: str
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_nonempty(self.target_deck, "target_deck")
        _validate_nonempty(self.note_type, "note_type")
        _validate_source_label(self.source_label)
        _validate_counts(
            cards_to_write=self.cards_to_write,
            warning_count=self.warning_count,
            blocking_count=self.blocking_count,
        )
        if not self.field_mapping or not all(
            isinstance(item, str) and item.strip() for item in self.field_mapping
        ):
            raise ValueError("field_mapping must contain non-empty labels.")
        _validate_nonempty(self.duplicate_behavior, "duplicate_behavior")
        _validate_tags(self.tags)

    def __repr__(self) -> str:
        return (
            "WriteSummary("
            f"cards_to_write={self.cards_to_write}, warning_count={self.warning_count}, "
            f"blocking_count={self.blocking_count}, tag_count={len(self.tags)}, "
            f"field_mapping_count={len(self.field_mapping)})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "cards_to_write": self.cards_to_write,
            "warning_count": self.warning_count,
            "blocking_count": self.blocking_count,
            "duplicate_behavior": self.duplicate_behavior,
            "tag_count": len(self.tags),
            "field_mapping_count": len(self.field_mapping),
            "source_label": self.source_label,
        }


@dataclass(frozen=True, repr=False)
class WriteResultSummary:
    written_count: int
    skipped_duplicate_count: int
    failed_count: int
    target_deck: str = field(repr=False)
    tags: tuple[str, ...]
    note_type: str = field(default="", repr=False)
    source_label: str = field(default="", repr=False)
    timestamp_utc: str = field(default="", repr=False)
    batch_id: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_counts(
            written_count=self.written_count,
            skipped_duplicate_count=self.skipped_duplicate_count,
            failed_count=self.failed_count,
        )
        _validate_nonempty(self.target_deck, "target_deck")
        _validate_tags(self.tags)
        _validate_optional_trace_metadata(
            batch_id=self.batch_id,
            timestamp_utc=self.timestamp_utc,
            note_type=self.note_type,
            source_label=self.source_label,
        )

    def __repr__(self) -> str:
        return (
            "WriteResultSummary("
            f"written_count={self.written_count}, "
            f"skipped_duplicate_count={self.skipped_duplicate_count}, "
            f"failed_count={self.failed_count}, tag_count={len(self.tags)})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "written_count": self.written_count,
            "skipped_duplicate_count": self.skipped_duplicate_count,
            "failed_count": self.failed_count,
            "tag_count": len(self.tags),
            "batch_id": self.batch_id or None,
            "timestamp_utc": self.timestamp_utc or None,
            "note_type": self.note_type or None,
            "source_label": self.source_label or None,
        }


@dataclass(frozen=True, repr=False)
class LastWriteBatchRecord:
    snapshot_id: str
    created_note_ids: tuple[int, ...] = field(repr=False)
    requested_count: int
    skipped_count: int
    failed_count: int
    target_deck: str = field(repr=False)
    tags: tuple[str, ...]
    source_type: SourceType
    batch_id: str = field(default="", repr=False)
    timestamp_utc: str = field(default="", repr=False)
    note_type: str = field(default="", repr=False)
    source_label: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _validate_nonempty(self.snapshot_id, "snapshot_id")
        if not self.created_note_ids or any(
            isinstance(note_id, bool)
            or not isinstance(note_id, int)
            or note_id <= 0
            for note_id in self.created_note_ids
        ):
            raise ValueError("created_note_ids must contain positive integer ids.")
        if len(set(self.created_note_ids)) != len(self.created_note_ids):
            raise ValueError("created_note_ids must be unique.")
        _validate_counts(
            requested_count=self.requested_count,
            skipped_count=self.skipped_count,
            failed_count=self.failed_count,
        )
        _validate_nonempty(self.target_deck, "target_deck")
        _validate_tags(self.tags)
        if not isinstance(self.source_type, SourceType):
            raise ValueError("source_type must be SourceType.")
        _validate_optional_trace_metadata(
            batch_id=self.batch_id,
            timestamp_utc=self.timestamp_utc,
            note_type=self.note_type,
            source_label=self.source_label,
        )

    @property
    def written_count(self) -> int:
        return len(self.created_note_ids)

    def __repr__(self) -> str:
        return (
            "LastWriteBatchRecord("
            f"written_count={self.written_count}, requested_count={self.requested_count}, "
            f"skipped_count={self.skipped_count}, failed_count={self.failed_count}, "
            f"tag_count={len(self.tags)}, source_type={self.source_type.value!r})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "snapshot_id_present": bool(self.snapshot_id),
            "created_note_count": len(self.created_note_ids),
            "requested_count": self.requested_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "tag_count": len(self.tags),
            "source_type": self.source_type.value,
            "batch_id": self.batch_id or None,
            "timestamp_utc": self.timestamp_utc or None,
            "note_type": self.note_type or None,
            "source_label": self.source_label or None,
        }


def build_write_summary(**values) -> WriteSummary:
    normalized = dict(values)
    normalized["field_mapping"] = tuple(normalized.get("field_mapping", ()))
    normalized["tags"] = _normalized_tags(normalized.get("tags", ()))
    return WriteSummary(**normalized)


def build_write_result_summary(**values) -> WriteResultSummary:
    normalized = dict(values)
    normalized["tags"] = _normalized_tags(normalized.get("tags", ()))
    return WriteResultSummary(**normalized)


def create_last_write_batch_record(
    *,
    snapshot_id: str,
    created_note_ids: tuple[int, ...],
    requested_count: int,
    skipped_count: int,
    failed_count: int,
    target_deck: str,
    note_type: str,
    tags: tuple[str, ...],
    source_type: SourceType,
    source_label: str | None = None,
    language: str = "en",
    batch_id: str | None = None,
    timestamp_utc: str | None = None,
) -> LastWriteBatchRecord:
    """Create one in-memory write trace with safe UTC and batch metadata."""

    resolved_batch_id = batch_id or f"batch-{uuid.uuid4().hex}"
    resolved_timestamp = timestamp_utc or _current_utc_timestamp()
    resolved_source_label = (
        safe_source_label(source_type, language)
        if source_label is None
        else source_label
    )
    return LastWriteBatchRecord(
        snapshot_id=snapshot_id,
        created_note_ids=created_note_ids,
        requested_count=requested_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        target_deck=target_deck,
        tags=tags,
        source_type=source_type,
        batch_id=resolved_batch_id,
        timestamp_utc=resolved_timestamp,
        note_type=note_type,
        source_label=resolved_source_label,
    )


def _normalized_tags(values: Iterable[object]) -> tuple[str, ...]:
    tags = []
    seen = set()
    for value in values:
        tag = normalize_tag(value)
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tuple(tags)


def _validate_tags(tags: tuple[str, ...]) -> None:
    if not isinstance(tags, tuple) or not tags:
        raise ValueError("tags must be a non-empty tuple.")
    for tag in tags:
        if normalize_tag(tag) != tag or _SECRET_MARKER.search(tag):
            raise ValueError("tags must contain normalized non-sensitive values.")


def _validate_source_label(value: str) -> None:
    _validate_nonempty(value, "source_label")
    if (
        _WINDOWS_PATH.search(value)
        or "/" in value
        or "\\" in value
        or _SECRET_MARKER.search(value)
    ):
        raise ValueError("source_label must be a short non-sensitive label.")


def _validate_optional_trace_metadata(
    *,
    batch_id: str,
    timestamp_utc: str,
    note_type: str,
    source_label: str,
) -> None:
    for value, name in (
        (batch_id, "batch_id"),
        (timestamp_utc, "timestamp_utc"),
        (note_type, "note_type"),
        (source_label, "source_label"),
    ):
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string.")
    if batch_id:
        if (
            not _TRACE_ID.fullmatch(batch_id)
            or _SECRET_MARKER.search(batch_id)
            or "/" in batch_id
            or "\\" in batch_id
        ):
            raise ValueError("batch_id must be a short non-sensitive identifier.")
    if timestamp_utc:
        _validate_utc_timestamp(timestamp_utc)
    if note_type:
        _validate_safe_display_label(note_type, "note_type")
    if source_label:
        _validate_source_label(source_label)


def _validate_safe_display_label(value: str, name: str) -> None:
    _validate_nonempty(value, name)
    if (
        _WINDOWS_PATH.search(value)
        or "/" in value
        or "\\" in value
        or _SECRET_MARKER.search(value)
    ):
        raise ValueError(f"{name} must be a short non-sensitive label.")


def _validate_utc_timestamp(value: str) -> None:
    if not _UTC_TIMESTAMP.fullmatch(value):
        raise ValueError("timestamp_utc must be an ISO-8601 UTC timestamp ending in Z.")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        raise ValueError(
            "timestamp_utc must be an ISO-8601 UTC timestamp ending in Z."
        ) from None
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp_utc must use UTC.")


def _current_utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def _validate_nonempty(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")


def _validate_counts(**values: int) -> None:
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer.")
