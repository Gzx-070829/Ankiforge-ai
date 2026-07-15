"""Read-only normalized duplicate preview for beginner candidate cards."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence

from ..anki_writer.field_content import (
    duplicate_key_from_plain_text,
    plain_text_from_anki_html,
)
from .beginner_flow_models import BeginnerCandidateCardPreview
from .read_only_anki_targets import BeginnerFieldMappingPreview


DUPLICATE_CHECK_ERROR_COPY = "无法完成重复检查。没有写入 Anki。"
DUPLICATE_CHECK_BLOCKED_COPY = "请先完成目标牌组、笔记类型和字段映射。"
DUPLICATE_CHECK_SCOPE_COPY = (
    "当前只是只读检查；在当前 collection 可读范围内检查所选笔记类型。"
    "没有写入 Anki。"
)


class BeginnerDuplicateStatus(str, Enum):
    NO_OBVIOUS_DUPLICATE = "no_obvious_duplicate"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    UNABLE_TO_CHECK = "unable_to_check"


class BeginnerDuplicatePreviewState(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"


@dataclass(frozen=True, repr=False)
class _ExistingNoteFields:
    note_id: int
    front_key: str
    front_preview: str
    back_key: str
    back_preview: str


@dataclass(frozen=True, repr=False)
class BeginnerDuplicateCandidateResult:
    candidate_id: str
    status: BeginnerDuplicateStatus
    matched_fields: tuple[str, ...] = field(default_factory=tuple)
    matched_note_id: Optional[int] = None
    matched_field_preview: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be a non-empty string.")
        if not isinstance(self.status, BeginnerDuplicateStatus):
            raise ValueError("status must be a BeginnerDuplicateStatus.")
        if not isinstance(self.matched_fields, tuple) or not all(
            isinstance(item, str) and item for item in self.matched_fields
        ):
            raise ValueError("matched_fields must contain non-empty strings.")
        if self.matched_note_id is not None and (
            isinstance(self.matched_note_id, bool)
            or not isinstance(self.matched_note_id, int)
        ):
            raise ValueError("matched_note_id must be an integer or None.")
        if not isinstance(self.matched_field_preview, str):
            raise ValueError("matched_field_preview must be a string.")

    @property
    def status_copy(self) -> str:
        return {
            BeginnerDuplicateStatus.NO_OBVIOUS_DUPLICATE: "未发现明显重复",
            BeginnerDuplicateStatus.POSSIBLE_DUPLICATE: "可能重复",
            BeginnerDuplicateStatus.UNABLE_TO_CHECK: "无法检查",
        }[self.status]

    def __repr__(self) -> str:
        return (
            "BeginnerDuplicateCandidateResult("
            f"candidate_id={self.candidate_id!r}, status={self.status.value!r}, "
            f"matched_fields={self.matched_fields!r}, "
            f"matched_note_id={self.matched_note_id!r}, "
            f"matched_preview_chars={len(self.matched_field_preview)})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status.value,
            "matched_fields": self.matched_fields,
            "matched_note_id": self.matched_note_id,
            "matched_preview_chars": len(self.matched_field_preview),
        }


@dataclass(frozen=True)
class BeginnerDuplicateCheckPreview:
    state: BeginnerDuplicatePreviewState
    results: tuple[BeginnerDuplicateCandidateResult, ...] = field(
        default_factory=tuple,
        repr=False,
    )
    user_message: str = ""

    @property
    def success(self) -> bool:
        return self.state is BeginnerDuplicatePreviewState.SUCCESS

    @property
    def read_only(self) -> bool:
        return True

    @property
    def will_write_to_anki(self) -> bool:
        return False

    def to_safe_dict(self) -> dict:
        return {
            "state": self.state.value,
            "result_count": len(self.results),
            "possible_duplicate_count": sum(
                item.status is BeginnerDuplicateStatus.POSSIBLE_DUPLICATE
                for item in self.results
            ),
            "user_message": self.user_message,
            "read_only": self.read_only,
            "will_write_to_anki": self.will_write_to_anki,
        }


class ReadOnlyDuplicateCheckAdapter:
    """Read mapped fields from existing notes and never mutate collection state."""

    def __init__(self, collection):
        self._collection = collection

    def check(
        self,
        candidates: Sequence[BeginnerCandidateCardPreview],
        mapping: BeginnerFieldMappingPreview,
    ) -> BeginnerDuplicateCheckPreview:
        if isinstance(candidates, (str, bytes)) or not isinstance(
            candidates,
            Sequence,
        ):
            raise ValueError("candidates must be a sequence.")
        resolved_candidates = tuple(candidates)
        if not resolved_candidates or not all(
            isinstance(item, BeginnerCandidateCardPreview)
            for item in resolved_candidates
        ):
            return _blocked_preview()
        if not isinstance(mapping, BeginnerFieldMappingPreview):
            return _blocked_preview()

        try:
            existing = self._read_existing_notes(mapping)
        except Exception:
            return BeginnerDuplicateCheckPreview(
                state=BeginnerDuplicatePreviewState.ERROR,
                results=tuple(
                    BeginnerDuplicateCandidateResult(
                        candidate_id=item.id,
                        status=BeginnerDuplicateStatus.UNABLE_TO_CHECK,
                    )
                    for item in resolved_candidates
                ),
                user_message=DUPLICATE_CHECK_ERROR_COPY,
            )

        results = tuple(
            _match_candidate(candidate, existing, mapping)
            for candidate in resolved_candidates
        )
        return BeginnerDuplicateCheckPreview(
            state=BeginnerDuplicatePreviewState.SUCCESS,
            results=results,
            user_message=DUPLICATE_CHECK_SCOPE_COPY,
        )

    def _read_existing_notes(self, mapping):
        note_ids = self._collection.db.list(
            "select id from notes where mid = ?",
            mapping.note_type.id,
        )
        existing = []
        for note_id in note_ids:
            note = self._collection.get_note(note_id)
            front_preview = plain_text_from_anki_html(
                _note_field(note, mapping.front_field)
            )
            back_preview = plain_text_from_anki_html(
                _note_field(note, mapping.back_field)
            )
            existing.append(
                _ExistingNoteFields(
                    note_id=_note_id(note, note_id),
                    front_key=duplicate_key_from_plain_text(front_preview),
                    front_preview=front_preview,
                    back_key=duplicate_key_from_plain_text(back_preview),
                    back_preview=back_preview,
                )
            )
        return tuple(existing)


def normalize_duplicate_preview_text(value: object) -> str:
    """Strip, case-fold, and collapse consecutive whitespace."""

    return duplicate_key_from_plain_text(str(value or ""))


def _match_candidate(candidate, existing, mapping):
    candidate_front = duplicate_key_from_plain_text(candidate.front_preview)
    candidate_back = duplicate_key_from_plain_text(candidate.back_preview)
    for note in existing:
        matched_fields = []
        preview = ""
        if candidate_front and candidate_front == note.front_key:
            matched_fields.append(mapping.front_field)
            preview = note.front_preview
        if candidate_back and candidate_back == note.back_key:
            matched_fields.append(mapping.back_field)
            if not preview:
                preview = note.back_preview
        if matched_fields:
            return BeginnerDuplicateCandidateResult(
                candidate_id=candidate.id,
                status=BeginnerDuplicateStatus.POSSIBLE_DUPLICATE,
                matched_fields=tuple(matched_fields),
                matched_note_id=note.note_id,
                matched_field_preview=_short_preview(preview),
            )
    return BeginnerDuplicateCandidateResult(
        candidate_id=candidate.id,
        status=BeginnerDuplicateStatus.NO_OBVIOUS_DUPLICATE,
    )


def _note_id(note, fallback: int) -> int:
    value = note.get("id") if isinstance(note, dict) else getattr(note, "id", None)
    if isinstance(value, bool) or not isinstance(value, int):
        value = fallback
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("note id must be an integer.")
    return value


def _note_field(note, field_name: str) -> str:
    try:
        value = note[field_name]
    except (KeyError, TypeError):
        raise ValueError("mapped note field is unavailable.") from None
    return str(value or "")


def _short_preview(value: object, max_chars: int = 80) -> str:
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"


def _blocked_preview() -> BeginnerDuplicateCheckPreview:
    return BeginnerDuplicateCheckPreview(
        state=BeginnerDuplicatePreviewState.BLOCKED,
        user_message=DUPLICATE_CHECK_BLOCKED_COPY,
    )
