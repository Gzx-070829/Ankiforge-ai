"""Display-only final confirmation summaries for the beginner walkthrough."""

from dataclasses import dataclass, field
from typing import Optional

from .beginner_flow_models import (
    BEGINNER_REVIEW_DECISION_COPY,
    BeginnerArtifactState,
    BeginnerCandidateCardPreview,
    BeginnerFlowSession,
    BeginnerReviewDecision,
)
from .read_only_anki_targets import BeginnerFieldMappingPreview
from .read_only_duplicate_check import (
    BeginnerDuplicateCheckPreview,
    BeginnerDuplicatePreviewState,
    BeginnerDuplicateStatus,
)


FINAL_CONFIRMATION_SAFETY_COPY = (
    "当前只是最终确认预览，尚未写入 Anki。"
)
FINAL_CONFIRMATION_FUTURE_COPY = (
    "只有点击下方真实写入按钮并通过二次确认，才会创建 Anki note。"
)
FINAL_CONFIRMATION_EMPTY_COPY = (
    "可以先查看缺少哪些条件；当前不会创建 note，也不会修改 Anki。"
)


@dataclass(frozen=True, repr=False)
class BeginnerFinalConfirmationCardPreview:
    """One content-safe-at-repr card row in the display-only summary."""

    candidate_id: str
    front: str = field(repr=False)
    back: str = field(repr=False)
    source: str = field(repr=False)
    review_decision: Optional[BeginnerReviewDecision]
    review_copy: str
    duplicate_status: Optional[BeginnerDuplicateStatus]
    duplicate_copy: str
    attention_copy: str

    def __repr__(self) -> str:
        return (
            "BeginnerFinalConfirmationCardPreview("
            f"candidate_id={self.candidate_id!r}, "
            f"front_chars={len(self.front)}, back_chars={len(self.back)}, "
            f"source_chars={len(self.source)}, "
            f"review_decision={self.review_decision!r}, "
            f"duplicate_status={self.duplicate_status!r})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "front_chars": len(self.front),
            "back_chars": len(self.back),
            "source_chars": len(self.source),
            "review_decision": (
                self.review_decision.value if self.review_decision else None
            ),
            "duplicate_status": (
                self.duplicate_status.value if self.duplicate_status else None
            ),
        }


@dataclass(frozen=True, repr=False)
class BeginnerFinalConfirmationPreview:
    """An in-memory summary that has no write-command behavior."""

    cards: tuple[BeginnerFinalConfirmationCardPreview, ...] = field(
        default_factory=tuple,
        repr=False,
    )
    deck_name: str = ""
    note_type_name: str = ""
    front_field: str = ""
    back_field: str = ""
    source_field: Optional[str] = None
    missing_conditions: tuple[str, ...] = field(default_factory=tuple)
    possible_duplicate_count: int = 0

    @property
    def candidate_count(self) -> int:
        return len(self.cards)

    @property
    def requirements_complete(self) -> bool:
        return not self.missing_conditions

    @property
    def read_only(self) -> bool:
        return True

    @property
    def real_write_available(self) -> bool:
        return False

    @property
    def will_write_to_anki(self) -> bool:
        return False

    def __repr__(self) -> str:
        return (
            "BeginnerFinalConfirmationPreview("
            f"candidate_count={self.candidate_count}, "
            f"deck_selected={bool(self.deck_name)}, "
            f"note_type_selected={bool(self.note_type_name)}, "
            f"missing_condition_count={len(self.missing_conditions)}, "
            f"possible_duplicate_count={self.possible_duplicate_count})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "candidate_count": self.candidate_count,
            "deck_selected": bool(self.deck_name),
            "note_type_selected": bool(self.note_type_name),
            "front_field_selected": bool(self.front_field),
            "back_field_selected": bool(self.back_field),
            "source_field_selected": bool(self.source_field),
            "missing_conditions": self.missing_conditions,
            "possible_duplicate_count": self.possible_duplicate_count,
            "requirements_complete": self.requirements_complete,
            "read_only": self.read_only,
            "real_write_available": self.real_write_available,
            "will_write_to_anki": self.will_write_to_anki,
        }


def build_beginner_final_confirmation_preview(
    session: BeginnerFlowSession,
    mapping: Optional[BeginnerFieldMappingPreview],
    duplicate_preview: Optional[BeginnerDuplicateCheckPreview],
) -> BeginnerFinalConfirmationPreview:
    """Collect current in-memory previews without preparing a write operation."""

    if not isinstance(session, BeginnerFlowSession):
        raise ValueError("session must be a BeginnerFlowSession.")
    if mapping is not None and not isinstance(mapping, BeginnerFieldMappingPreview):
        raise ValueError("mapping must be a BeginnerFieldMappingPreview or None.")
    if duplicate_preview is not None and not isinstance(
        duplicate_preview,
        BeginnerDuplicateCheckPreview,
    ):
        raise ValueError(
            "duplicate_preview must be a BeginnerDuplicateCheckPreview or None."
        )

    mapping_current = bool(
        mapping is not None
        and session.anki_mapping_preview_state is BeginnerArtifactState.CURRENT
        and mapping.deck.id == session.selected_anki_deck_id
        and mapping.note_type.id == session.selected_anki_note_type_id
        and mapping.front_field == session.mapped_front_field
        and mapping.back_field == session.mapped_back_field
        and mapping.source_field == session.mapped_source_field
    )
    effective_mapping = mapping if mapping_current else None
    candidates = tuple(session.candidate_card_previews)
    candidate_ids = {item.id for item in candidates}
    duplicate_results = (
        {item.candidate_id: item for item in duplicate_preview.results}
        if duplicate_preview is not None
        and duplicate_preview.state is BeginnerDuplicatePreviewState.SUCCESS
        else {}
    )
    cards = tuple(
        _build_card_preview(
            candidate,
            session.candidate_review_decisions.get(candidate.id),
            duplicate_results.get(candidate.id),
        )
        for candidate in candidates
    )

    missing = []
    if not candidates:
        missing.append("没有候选卡")
    elif set(session.candidate_review_decisions) & candidate_ids != candidate_ids:
        missing.append("候选卡还没有全部审核")
    if session.selected_anki_deck_id is None or not session.selected_anki_deck_name:
        missing.append("没有选择目标牌组")
    if (
        session.selected_anki_note_type_id is None
        or not session.selected_anki_note_type_name
    ):
        missing.append("没有选择笔记类型")
    if (
        effective_mapping is None
        or not session.mapped_front_field
        or not session.mapped_back_field
    ):
        missing.append("没有完成正面和背面的字段映射")
    duplicate_complete = bool(
        duplicate_preview is not None
        and session.duplicate_check_preview_state is BeginnerArtifactState.CURRENT
        and duplicate_preview.state is BeginnerDuplicatePreviewState.SUCCESS
        and set(duplicate_results) == candidate_ids
        and candidates
    )
    if not duplicate_complete:
        missing.append("重复检查尚未完成")

    return BeginnerFinalConfirmationPreview(
        cards=cards,
        deck_name=session.selected_anki_deck_name,
        note_type_name=session.selected_anki_note_type_name,
        front_field=effective_mapping.front_field if effective_mapping else "",
        back_field=effective_mapping.back_field if effective_mapping else "",
        source_field=effective_mapping.source_field if effective_mapping else None,
        missing_conditions=tuple(missing),
        possible_duplicate_count=sum(
            item.duplicate_status is BeginnerDuplicateStatus.POSSIBLE_DUPLICATE
            for item in cards
        ),
    )


def _build_card_preview(candidate, review_decision, duplicate_result):
    review_copy = (
        BEGINNER_REVIEW_DECISION_COPY[review_decision]
        if review_decision is not None
        else "尚未审核"
    )
    duplicate_status = duplicate_result.status if duplicate_result else None
    duplicate_copy = (
        duplicate_result.status_copy if duplicate_result else "尚未完成检查"
    )
    attention = []
    if review_decision is None:
        attention.append("需要注意：尚未审核")
    elif review_decision is BeginnerReviewDecision.SKIP_FOR_NOW:
        attention.append("本次写入应跳过：暂时不要")
    elif review_decision is BeginnerReviewDecision.NEEDS_CHANGES:
        attention.append("本次写入应跳过：需要修改")
    if duplicate_status is BeginnerDuplicateStatus.POSSIBLE_DUPLICATE:
        attention.append("本次写入默认跳过：可能重复")
    elif duplicate_status is BeginnerDuplicateStatus.UNABLE_TO_CHECK:
        attention.append("需要注意：无法检查重复")
    if not attention:
        attention.append("本次预览保留；仍不代表写入授权")
    return BeginnerFinalConfirmationCardPreview(
        candidate_id=candidate.id,
        front=candidate.front_preview,
        back=candidate.back_preview,
        source=candidate.source_excerpt,
        review_decision=review_decision,
        review_copy=review_copy,
        duplicate_status=duplicate_status,
        duplicate_copy=duplicate_copy,
        attention_copy="；".join(attention),
    )
