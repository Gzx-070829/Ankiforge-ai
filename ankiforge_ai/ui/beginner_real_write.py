"""Prepare and explicitly gate one immutable beginner-mode write snapshot."""

from dataclasses import dataclass, field, replace
import hashlib
import json
from typing import Optional

from ..pipeline.write_traceability import build_default_tags, safe_source_label
from ..pipeline.field_mapping import assess_field_mapping
from ..pipeline.write_safety import (
    WriteSafetySnapshot,
    evaluate_write_safety,
)
from ..anki_writer.minimal_write import (
    BeginnerWriteCardCommand,
    BeginnerWriteCommand,
)
from .beginner_final_confirmation import BeginnerFinalConfirmationPreview
from .beginner_flow_models import (
    BeginnerArtifactState,
    BeginnerFlowSession,
    BeginnerReviewDecision,
)
from .read_only_anki_targets import BeginnerFieldMappingPreview
from .read_only_duplicate_check import (
    BeginnerDuplicateCheckPreview,
    BeginnerDuplicatePreviewState,
    BeginnerDuplicateStatus,
)


WRITE_CONFIRMATION_DISCLOSURE_COPY = (
    "这一步会真正修改 Anki collection，并创建新的 note。"
)
WRITE_COMPLETION_TITLE = "写入完成，请在 Anki 中检查新卡片"
WRITE_IDLE_COPY = "请先生成最终确认预览；条件满足后才会开放真实写入。"


@dataclass(frozen=True, repr=False)
class BeginnerWritePreparation:
    command: Optional[BeginnerWriteCommand] = field(default=None, repr=False)
    missing_conditions: tuple[str, ...] = field(default_factory=tuple)
    skipped_candidate_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def can_write(self) -> bool:
        return self.command is not None and not self.missing_conditions

    @property
    def writable_count(self) -> int:
        return self.command.requested_count if self.command else 0

    @property
    def skipped_count(self) -> int:
        return len(self.skipped_candidate_ids)

    def __repr__(self) -> str:
        return (
            "BeginnerWritePreparation("
            f"can_write={self.can_write}, writable_count={self.writable_count}, "
            f"skipped_count={self.skipped_count}, "
            f"missing_condition_count={len(self.missing_conditions)})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "can_write": self.can_write,
            "writable_count": self.writable_count,
            "skipped_count": self.skipped_count,
            "missing_conditions": self.missing_conditions,
            "snapshot_id": self.command.snapshot_id if self.command else None,
        }


def prepare_beginner_write(
    session: BeginnerFlowSession,
    final_preview: Optional[BeginnerFinalConfirmationPreview],
    mapping: Optional[BeginnerFieldMappingPreview],
    duplicate_preview: Optional[BeginnerDuplicateCheckPreview],
) -> BeginnerWritePreparation:
    """Return a command only for reviewed, non-duplicate, current AI drafts."""

    if not isinstance(session, BeginnerFlowSession):
        raise ValueError("session must be a BeginnerFlowSession.")

    missing = []
    candidates = tuple(session.candidate_card_previews)
    candidate_ids = {item.id for item in candidates}
    final_current = bool(
        final_preview is not None
        and isinstance(final_preview, BeginnerFinalConfirmationPreview)
        and session.final_confirmation_preview_state is BeginnerArtifactState.CURRENT
        and {item.candidate_id for item in final_preview.cards} == candidate_ids
    )
    if not final_current:
        missing.append("没有当前最终确认预览")
    elif final_preview.missing_conditions:
        missing.extend(final_preview.missing_conditions)

    if session.candidate_origin != "real_ai_draft":
        missing.append("候选卡不是当前 AI 草稿")
    ai_candidate_ids = {
        f"candidate-{item.id}" for item in session.ai_candidate_card_drafts
    }
    if not candidates or candidate_ids != ai_candidate_ids:
        missing.append("没有可验证的当前 AI 候选卡")

    mapping_current = bool(
        mapping is not None
        and isinstance(mapping, BeginnerFieldMappingPreview)
        and session.anki_mapping_preview_state is BeginnerArtifactState.CURRENT
        and mapping.deck.id == session.selected_anki_deck_id
        and mapping.note_type.id == session.selected_anki_note_type_id
        and mapping.front_field == session.mapped_front_field
        and mapping.back_field == session.mapped_back_field
        and mapping.source_field == session.mapped_source_field
    )
    if not mapping_current:
        missing.append("没有当前目标和字段映射")
    mapping_assessment = (
        assess_field_mapping(
            session.selected_anki_note_type_fields,
            mapping.front_field,
            mapping.back_field,
            mapping.source_field,
            note_type_name=session.selected_anki_note_type_name,
            template_id=session.generation_settings.card_mode,
        )
        if mapping_current
        else None
    )
    mapping_complete = bool(
        mapping_current
        and mapping_assessment is not None
        and mapping_assessment.complete
    )
    if mapping_assessment is not None:
        if "mapped_fields_not_unique" in mapping_assessment.blocking_reasons:
            missing.append("正面、背面和来源不能重复使用同一字段")
        if "cloze_note_type_incompatible" in mapping_assessment.blocking_reasons:
            missing.append("当前笔记类型不支持 Cloze 写入")

    generation_complete = bool(
        session.ai_generation_state.value == "success"
        and session.ai_draft_state is BeginnerArtifactState.CURRENT
    )
    if not generation_complete:
        missing.append("AI 生成流程尚未结束")

    duplicate_results = (
        {item.candidate_id: item for item in duplicate_preview.results}
        if duplicate_preview is not None
        and isinstance(duplicate_preview, BeginnerDuplicateCheckPreview)
        and duplicate_preview.state is BeginnerDuplicatePreviewState.SUCCESS
        else {}
    )
    duplicate_current = bool(
        duplicate_preview is not None
        and session.duplicate_check_preview_state is BeginnerArtifactState.CURRENT
        and set(duplicate_results) == candidate_ids
        and candidates
    )
    if not duplicate_current:
        missing.append("重复检查尚未完成")
    elif any(
        item.status is BeginnerDuplicateStatus.UNABLE_TO_CHECK
        for item in duplicate_results.values()
    ):
        missing.append("有候选卡无法完成重复检查")

    writable = []
    skipped_ids = []
    if duplicate_current:
        for candidate in candidates:
            review = session.candidate_review_decisions.get(candidate.id)
            duplicate = duplicate_results[candidate.id]
            quality = session.candidate_quality_results.get(candidate.id)
            if (
                review is BeginnerReviewDecision.LOOKS_GOOD
                and quality is not None
                and quality.is_blocking
            ):
                missing.append("有审核保留的候选卡未通过质量硬性检查")
                skipped_ids.append(candidate.id)
                continue
            if (
                review is BeginnerReviewDecision.LOOKS_GOOD
                and duplicate.status
                is BeginnerDuplicateStatus.NO_OBVIOUS_DUPLICATE
            ):
                writable.append(candidate)
            else:
                skipped_ids.append(candidate.id)
    else:
        skipped_ids.extend(item.id for item in candidates)

    if not writable:
        missing.append("没有审核通过且未发现明显重复的候选卡")
    missing = list(dict.fromkeys(missing))
    if missing or not mapping_complete:
        return BeginnerWritePreparation(
            missing_conditions=tuple(missing),
            skipped_candidate_ids=tuple(skipped_ids),
        )

    source_label = safe_source_label(session.source_type, "en")
    tags = build_default_tags(session.generation_settings, session.source_type)
    cards = tuple(
        BeginnerWriteCardCommand(
            candidate_id=item.id,
            front=item.front_preview,
            back=item.back_preview,
            source=source_label,
        )
        for item in writable
    )
    snapshot_id = _snapshot_id(session, mapping, cards, tags)
    command = BeginnerWriteCommand(
        snapshot_id=snapshot_id,
        deck_id=mapping.deck.id,
        deck_name=mapping.deck.name,
        note_type_id=mapping.note_type.id,
        note_type_name=mapping.note_type.name,
        front_field=mapping.front_field,
        back_field=mapping.back_field,
        source_field=mapping.source_field,
        cards=cards,
        skipped_count=len(skipped_ids),
        tags=tags,
        safety_snapshot=WriteSafetySnapshot(
            kept_count=len(cards),
            blocking_write_count=0,
            mapping_complete=mapping_complete,
            duplicate_check_complete=duplicate_current,
            final_confirmation_confirmed=False,
            target_valid=mapping_current,
            generation_complete=generation_complete,
        ),
    )
    if session.has_completed_write_snapshot(snapshot_id):
        return BeginnerWritePreparation(
            missing_conditions=("这一批候选卡已经完成过写入，不能重复写入",),
            skipped_candidate_ids=tuple(skipped_ids),
        )
    return BeginnerWritePreparation(
        command=command,
        skipped_candidate_ids=tuple(skipped_ids),
    )


def execute_beginner_write_if_confirmed(confirmed, writer, command):
    """Keep the writer call behind an explicit boolean confirmation gate."""

    if confirmed is not True:
        return None
    if not isinstance(command, BeginnerWriteCommand):
        raise ValueError("command must be a BeginnerWriteCommand.")
    if command.safety_snapshot is None:
        raise ValueError("write safety snapshot is required.")
    confirmed_snapshot = replace(
        command.safety_snapshot,
        final_confirmation_confirmed=True,
    )
    decision = evaluate_write_safety(confirmed_snapshot)
    if not decision.allowed:
        raise ValueError(
            "write safety gates failed: " + ", ".join(decision.blocking_reasons)
        )
    return writer.write(replace(command, safety_snapshot=confirmed_snapshot))


def _snapshot_id(session, mapping, cards, tags=()):
    payload = {
        "candidate_revision": session.candidate_revision,
        "review_revision": session.review_revision,
        "deck_id": mapping.deck.id,
        "note_type_id": mapping.note_type.id,
        "front_field": mapping.front_field,
        "back_field": mapping.back_field,
        "source_field": mapping.source_field,
        "tags": list(tags),
        "cards": [
            {
                "candidate_id": item.candidate_id,
                "front": item.front,
                "back": item.back,
                "source": item.source,
            }
            for item in cards
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
