"""Pure-Python state and copy models for the beginner read-only walkthrough."""

from collections.abc import Sequence
from dataclasses import dataclass, field, fields
from enum import Enum
import re
from types import MappingProxyType
from typing import Mapping, Optional


class BeginnerFlowStep(str, Enum):
    """Stable steps in the beginner walkthrough."""

    SELECT_MATERIAL = "select_material"
    INSPECT_RECOGNITION = "inspect_recognition"
    CHOOSE_KNOWLEDGE_POINTS = "choose_knowledge_points"
    REVIEW_CANDIDATE_CARDS = "review_candidate_cards"
    CHECK_BEFORE_WRITE = "check_before_write"
    COMPLETED_NO_WRITE = "completed_no_write"


BEGINNER_FLOW_STEP_ORDER = (
    BeginnerFlowStep.SELECT_MATERIAL,
    BeginnerFlowStep.INSPECT_RECOGNITION,
    BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS,
    BeginnerFlowStep.REVIEW_CANDIDATE_CARDS,
    BeginnerFlowStep.CHECK_BEFORE_WRITE,
    BeginnerFlowStep.COMPLETED_NO_WRITE,
)


@dataclass(frozen=True)
class BeginnerStepCopy:
    title: str
    description: str
    primary_action: str
    empty_state: str


BEGINNER_STEP_COPY: Mapping[BeginnerFlowStep, BeginnerStepCopy] = MappingProxyType(
    {
        BeginnerFlowStep.SELECT_MATERIAL: BeginnerStepCopy(
            title="选择学习材料",
            description="选择一份 Markdown 学习材料，作为本次离线演练的起点。",
            primary_action="选择学习材料",
            empty_state="尚未选择材料。选择后，内容只用于当前内存会话。",
        ),
        BeginnerFlowStep.INSPECT_RECOGNITION: BeginnerStepCopy(
            title="查看系统识别了什么",
            description="查看当前材料经离线演练规则识别出的知识点，再继续。",
            primary_action="查看识别结果",
            empty_state="尚无材料预览。请先输入学习材料。",
        ),
        BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS: BeginnerStepCopy(
            title="选择要制卡的知识点",
            description="从刚才的离线识别结果中挑选本次想继续查看的知识点。",
            primary_action="确认知识点选择",
            empty_state="当前材料没有可选知识点。请返回并调整材料。",
        ),
        BeginnerFlowStep.REVIEW_CANDIDATE_CARDS: BeginnerStepCopy(
            title="审核候选卡",
            description="逐张查看正面、背面和来源，并用普通中文留下本次选择。",
            primary_action="继续",
            empty_state="还没有候选卡。请先回到上一步选择知识点。",
        ),
        BeginnerFlowStep.CHECK_BEFORE_WRITE: BeginnerStepCopy(
            title="查看距离真正写入还缺哪些条件",
            description="了解未来真正写入前仍需确认的五类信息；这里不授予权限。",
            primary_action="继续",
            empty_state="尚无可检查的审核结果。请先完成人工审核。",
        ),
        BeginnerFlowStep.COMPLETED_NO_WRITE: BeginnerStepCopy(
            title="演练完成，尚未写入 Anki",
            description="你已看完本次只读流程；所有结果仍停留在当前内存会话。",
            primary_action="结束演练",
            empty_state="尚未走完前面的演练步骤。",
        ),
    }
)


BEGINNER_SAFETY_STATUS_COPY = (
    "当前为离线只读演练",
    "不会联网",
    "不会调用 Provider",
    "不会读取 API Key",
    "不会执行 duplicate check",
    "不会访问 Anki collection",
    "不会写入 Anki",
    "关闭后本次演练丢弃",
)


BEGINNER_GUIDE_STEP_NOTES: Mapping[BeginnerFlowStep, str] = MappingProxyType(
    {
        BeginnerFlowStep.SELECT_MATERIAL: (
            "请在下方输入或粘贴学习材料。内容只保留在当前窗口。"
        ),
        BeginnerFlowStep.INSPECT_RECOGNITION: (
            "当前使用离线演练识别，不会联网，也不会调用 AI。"
        ),
        BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS: (
            "勾选的知识点只保留在当前窗口，并会传递到候选卡预览。"
        ),
        BeginnerFlowStep.REVIEW_CANDIDATE_CARDS: (
            "这些候选卡来自你刚才选择的知识点。"
        ),
        BeginnerFlowStep.CHECK_BEFORE_WRITE: (
            "本步骤只解释未来还需检查的事项，尚未产生授权。"
        ),
        BeginnerFlowStep.COMPLETED_NO_WRITE: BEGINNER_STEP_COPY[
            BeginnerFlowStep.COMPLETED_NO_WRITE
        ].description,
    }
)


BEGINNER_GUIDE_SAFETY_COPY = (
    "当前是离线只读演练",
    "不会联网",
    "不会调用 AI",
    "不会写入 Anki",
    "关闭后丢弃本次内容",
)


BEGINNER_TERM_COPY: Mapping[str, str] = MappingProxyType(
    {
        "Human Review": "人工审核",
        "Write Eligibility": "是否满足未来写入条件",
        "Write Plan": "未来写入方式预览",
        "Final confirmation contract": "真正写入前还需确认什么",
        "Provider draft": "AI 服务草稿",
        "GeneratedCard": "正式待写入卡片",
        "WriteReadyPreviewItem": "写入就绪对象",
    }
)


REVIEW_STATE_EXPLANATIONS: Mapping[str, str] = MappingProxyType(
    {
        "approved": "仅表示当前人工审核草稿通过，不代表写入授权。",
        "eligible": "仅表示预览中的条件看起来满足，不代表写入授权。",
        "ready_preview": "仅表示未来写入方式的只读预览可展示，不代表写入授权。",
        "ready_for_future_confirmation": (
            "仅表示可以解释未来仍需确认的事项，不代表写入授权。"
        ),
    }
)


class BeginnerReviewDecision(str, Enum):
    """Plain-language choices for one disposable candidate review."""

    LOOKS_GOOD = "looks_good"
    NEEDS_CHANGES = "needs_revision"
    SKIP_FOR_NOW = "skip_for_now"


BEGINNER_REVIEW_DECISION_COPY: Mapping[BeginnerReviewDecision, str] = (
    MappingProxyType(
        {
            BeginnerReviewDecision.LOOKS_GOOD: "看起来可以",
            BeginnerReviewDecision.NEEDS_CHANGES: "需要修改",
            BeginnerReviewDecision.SKIP_FOR_NOW: "暂时不要",
        }
    )
)


BEGINNER_REVIEW_SAFETY_NOTE = (
    "你的选择只用于本次离线演练，不会写入 Anki。"
)


BEGINNER_PREWRITE_SUMMARY = (
    "当前只是离线演练。即使你已经审核候选卡，也不会写入 Anki。"
)


@dataclass(frozen=True)
class BeginnerFutureConditionCopy:
    id: str
    title: str
    status: str
    explanation: str


BEGINNER_FUTURE_CONDITIONS = (
    BeginnerFutureConditionCopy(
        id="target_deck",
        title="目标牌组",
        status="未来需要确认",
        explanation="未来需要确认卡片应放到哪个牌组。",
    ),
    BeginnerFutureConditionCopy(
        id="note_type",
        title="笔记类型",
        status="未来需要确认",
        explanation="未来需要确认卡片采用哪一种笔记类型。",
    ),
    BeginnerFutureConditionCopy(
        id="field_mapping",
        title="字段映射",
        status="未来需要确认",
        explanation="未来需要确认正面、背面和来源分别对应哪些字段。",
    ),
    BeginnerFutureConditionCopy(
        id="duplicate_check",
        title="重复检查",
        status="未来需要确认",
        explanation="未来需要在受控流程中检查是否存在重复内容。",
    ),
    BeginnerFutureConditionCopy(
        id="final_confirmation",
        title="最终确认",
        status="未来需要确认",
        explanation="未来仍需要一次独立的最终确认。",
    ),
)


BEGINNER_TECHNICAL_DETAILS_COPY = (
    "人工审核：记录本次演练中的选择，不代表写入授权。",
    "是否满足未来写入条件：这里只说明未来还需检查什么，不代表写入授权。",
    "未来写入方式预览：本次没有创建正式待写入对象，不代表写入授权。",
    "真正写入前还需确认什么：这里只读列出未来事项，不代表写入授权。",
)


COMPLETION_TITLE = "演练完成，尚未写入 Anki"
COMPLETION_SUMMARY = "本次流程仅用于理解和检查，未产生任何真实写入。"
COMPLETION_FACTS = (
    "未创建 note",
    "未修改卡组",
    "未保存本次演练",
    "未联网",
    "未调用 provider",
)


ADVANCED_WORKBENCH_WARNING = (
    "旧版工作台（高级）包含开发/调试入口，可能包含真实 Anki 写入入口。"
    "请确认你理解风险后再进入。"
)


class BeginnerArtifactState(str, Enum):
    """Whether an in-memory result is absent, current, or explicitly cleared."""

    EMPTY = "empty"
    CURRENT = "current"
    CLEARED = "cleared"


@dataclass(frozen=True, repr=False)
class BeginnerKnowledgePointPreview:
    """A disposable, non-pipeline knowledge-point preview."""

    id: str
    title: str
    explanation: str
    source_excerpt: str

    def __repr__(self) -> str:
        return (
            "BeginnerKnowledgePointPreview("
            f"id={self.id!r}, title_chars={len(self.title)}, "
            f"source_chars={len(self.source_excerpt)})"
        )


@dataclass(frozen=True, repr=False)
class BeginnerCandidateCardPreview:
    """A disposable card-shaped preview that cannot be written anywhere."""

    id: str
    knowledge_point_id: str
    front_preview: str
    back_preview: str
    source_excerpt: str

    def __repr__(self) -> str:
        return (
            "BeginnerCandidateCardPreview("
            f"id={self.id!r}, knowledge_point_id={self.knowledge_point_id!r}, "
            f"front_chars={len(self.front_preview)}, "
            f"back_chars={len(self.back_preview)})"
        )


@dataclass
class BeginnerFlowSession:
    """In-memory navigation state for one non-persistent walkthrough."""

    current_step: BeginnerFlowStep = BeginnerFlowStep.SELECT_MATERIAL
    material_text: str = field(default="", repr=False)
    material_revision: int = 0
    recognition_revision: int = 0
    knowledge_selection_revision: int = 0
    candidate_revision: int = 0
    review_revision: int = 0
    selected_knowledge_point_count: int = 0
    candidate_count: int = 0
    reviewed_candidate_count: int = 0
    recognized_knowledge_points: tuple[BeginnerKnowledgePointPreview, ...] = field(
        default_factory=tuple,
        repr=False,
    )
    selected_knowledge_point_ids: tuple[str, ...] = field(
        default_factory=tuple,
        repr=False,
    )
    candidate_card_previews: tuple[BeginnerCandidateCardPreview, ...] = field(
        default_factory=tuple,
        repr=False,
    )
    candidate_review_decisions: dict[str, BeginnerReviewDecision] = field(
        default_factory=dict,
        repr=False,
    )
    recognition_state: BeginnerArtifactState = BeginnerArtifactState.EMPTY
    knowledge_selection_state: BeginnerArtifactState = BeginnerArtifactState.EMPTY
    candidate_cards_state: BeginnerArtifactState = BeginnerArtifactState.EMPTY
    review_state: BeginnerArtifactState = BeginnerArtifactState.EMPTY
    eligibility_state: BeginnerArtifactState = BeginnerArtifactState.EMPTY
    write_plan_preview_state: BeginnerArtifactState = BeginnerArtifactState.EMPTY
    final_confirmation_preview_state: BeginnerArtifactState = (
        BeginnerArtifactState.EMPTY
    )
    last_clearing_reason: Optional[str] = None
    closed: bool = False

    @property
    def is_offline_read_only(self) -> bool:
        return True

    @property
    def network_allowed(self) -> bool:
        return False

    @property
    def provider_call_allowed(self) -> bool:
        return False

    @property
    def api_key_read_allowed(self) -> bool:
        return False

    @property
    def duplicate_check_allowed(self) -> bool:
        return False

    @property
    def anki_collection_access_allowed(self) -> bool:
        return False

    @property
    def anki_write_allowed(self) -> bool:
        return False

    @property
    def persistent(self) -> bool:
        return False

    @property
    def material_char_count(self) -> int:
        return len(self.material_text)

    def material_preview(self, max_chars: int = 300) -> str:
        if isinstance(max_chars, bool) or not isinstance(max_chars, int):
            raise ValueError("max_chars must be an integer of at least 4.")
        if max_chars < 4:
            raise ValueError("max_chars must be an integer of at least 4.")
        if len(self.material_text) <= max_chars:
            return self.material_text
        return self.material_text[: max_chars - 3].rstrip() + "..."

    def update_material(self, text: str) -> None:
        """Keep material in memory and clear results derived from older text."""

        self._ensure_open()
        if not isinstance(text, str):
            raise ValueError("material text must be a string.")
        if text == self.material_text:
            return

        had_material = bool(self.material_text)
        self.material_text = text
        self.material_revision += 1
        self.current_step = BeginnerFlowStep.SELECT_MATERIAL
        self.recognized_knowledge_points = ()
        self.recognition_state = (
            BeginnerArtifactState.CLEARED
            if had_material
            else BeginnerArtifactState.EMPTY
        )
        self._clear_from_knowledge_selection("material_changed")

    def clear_material(self) -> None:
        """Remove in-memory material and every result derived from it."""

        self._ensure_open()
        if self.material_text:
            self.material_revision += 1
        self.material_text = ""
        self.current_step = BeginnerFlowStep.SELECT_MATERIAL
        self.recognized_knowledge_points = ()
        self.recognition_state = BeginnerArtifactState.CLEARED
        self._clear_from_knowledge_selection("material_cleared")

    def select_material(self) -> None:
        """Confirm that non-empty in-memory material may be previewed."""

        self._ensure_open()
        if not self.material_text.strip():
            raise ValueError("material text must not be empty.")
        self.refresh_mock_recognition_from_material()

    def refresh_mock_recognition_from_material(
        self,
        max_points: int = 6,
    ) -> tuple[BeginnerKnowledgePointPreview, ...]:
        """Build deterministic previews from only the current in-memory material."""

        self._ensure_open()
        if isinstance(max_points, bool) or not isinstance(max_points, int):
            raise ValueError("max_points must be a positive integer.")
        if max_points < 1:
            raise ValueError("max_points must be a positive integer.")

        fragments = tuple(
            fragment.strip()
            for fragment in re.split(r"[。！？；.!?;\r\n]+", self.material_text)
            if fragment.strip()
        )[:max_points]
        self.recognized_knowledge_points = tuple(
            BeginnerKnowledgePointPreview(
                id=f"kp-{index}",
                title=self._shorten(fragment, 36),
                explanation=f"这段材料主要在说明：{self._shorten(fragment, 90)}",
                source_excerpt=self._shorten(fragment, 140),
            )
            for index, fragment in enumerate(fragments, start=1)
        )
        self.recognition_revision += 1
        self.recognition_state = BeginnerArtifactState.CURRENT
        self._clear_from_knowledge_selection("recognition_refreshed")
        self.current_step = BeginnerFlowStep.INSPECT_RECOGNITION
        return self.recognized_knowledge_points

    def advance_guide(self) -> None:
        """Advance explanatory navigation without creating pipeline artifacts."""

        self._ensure_open()
        if self.current_step is BeginnerFlowStep.COMPLETED_NO_WRITE:
            raise ValueError("the beginner guide is already complete.")
        if (
            self.current_step is BeginnerFlowStep.SELECT_MATERIAL
            and not self.material_text.strip()
        ):
            raise ValueError("material text must not be empty.")
        current_index = BEGINNER_FLOW_STEP_ORDER.index(self.current_step)
        self.current_step = BEGINNER_FLOW_STEP_ORDER[current_index + 1]

    def mark_recognition_inspected(self) -> None:
        self._ensure_open()
        if self.recognition_state is not BeginnerArtifactState.CURRENT:
            raise ValueError("recognition must be current before it is inspected.")
        self.recognition_state = BeginnerArtifactState.CURRENT
        self.current_step = BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS

    def select_knowledge_points(self, ids: Sequence[str]) -> None:
        """Store a validated selection and invalidate every derived preview."""

        self._ensure_open()
        if isinstance(ids, (str, bytes)) or not isinstance(ids, Sequence):
            raise ValueError("ids must be a sequence of knowledge-point ids.")
        if self.recognition_state is not BeginnerArtifactState.CURRENT:
            raise ValueError("recognition must be current before knowledge selection.")
        if any(not isinstance(item, str) for item in ids):
            raise ValueError("knowledge-point ids must be strings.")
        known_ids = {point.id for point in self.recognized_knowledge_points}
        requested_ids = tuple(dict.fromkeys(ids))
        unknown_ids = set(requested_ids) - known_ids
        if unknown_ids:
            raise ValueError("unknown knowledge-point id.")

        ordered_ids = tuple(
            point.id
            for point in self.recognized_knowledge_points
            if point.id in requested_ids
        )
        if (
            self.knowledge_selection_state is BeginnerArtifactState.CURRENT
            and ordered_ids == self.selected_knowledge_point_ids
        ):
            self.current_step = BeginnerFlowStep.REVIEW_CANDIDATE_CARDS
            return

        self.knowledge_selection_revision += 1
        self.selected_knowledge_point_ids = ordered_ids
        self.selected_knowledge_point_count = len(ordered_ids)
        self.knowledge_selection_state = BeginnerArtifactState.CURRENT
        self._clear_from_candidates("knowledge_selection_changed")
        self.current_step = BeginnerFlowStep.REVIEW_CANDIDATE_CARDS

    def clear_knowledge_point_selection(self) -> None:
        self._ensure_open()
        self.knowledge_selection_revision += 1
        self._clear_from_knowledge_selection("knowledge_selection_cleared")
        self.current_step = BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS

    def build_candidate_previews_from_selection(
        self,
    ) -> tuple[BeginnerCandidateCardPreview, ...]:
        """Build card-shaped previews solely from the current selected IDs."""

        self._ensure_open()
        if self.knowledge_selection_state is not BeginnerArtifactState.CURRENT:
            raise ValueError("knowledge selection must be current before candidates.")
        selected_ids = set(self.selected_knowledge_point_ids)
        selected_points = tuple(
            point
            for point in self.recognized_knowledge_points
            if point.id in selected_ids
        )
        self.candidate_card_previews = tuple(
            BeginnerCandidateCardPreview(
                id=f"candidate-{point.id}",
                knowledge_point_id=point.id,
                front_preview=f"如何理解「{point.title}」？",
                back_preview=point.explanation,
                source_excerpt=point.source_excerpt,
            )
            for point in selected_points
        )
        self.candidate_revision += 1
        self.candidate_count = len(self.candidate_card_previews)
        self.candidate_cards_state = BeginnerArtifactState.CURRENT
        self._clear_from_review("candidate_previews_rebuilt")
        self.current_step = BeginnerFlowStep.REVIEW_CANDIDATE_CARDS
        return self.candidate_card_previews

    def set_candidate_review_decision(
        self,
        candidate_id: str,
        decision: Optional[BeginnerReviewDecision | str],
    ) -> None:
        """Update one disposable review marker and invalidate later previews."""

        self._ensure_open()
        candidate_ids = {item.id for item in self.candidate_card_previews}
        if candidate_id not in candidate_ids:
            raise ValueError("unknown candidate preview id.")
        normalized_decision = self._normalize_review_decision(decision)
        if decision is None:
            self.candidate_review_decisions.pop(candidate_id, None)
        else:
            self.candidate_review_decisions[candidate_id] = normalized_decision
        self.review_revision += 1
        self.reviewed_candidate_count = len(self.candidate_review_decisions)
        self.review_state = BeginnerArtifactState.CURRENT
        self._clear_prewrite_previews("candidate_review_changed")

    def complete_candidate_review(self) -> None:
        """Move to the explanatory check only after every preview has a choice."""

        self._ensure_open()
        if self.candidate_cards_state is not BeginnerArtifactState.CURRENT:
            raise ValueError("candidate cards must be current before review.")
        if self.candidate_count != len(self.candidate_review_decisions):
            raise ValueError("every candidate preview needs a review choice.")
        self.review_revision += 1
        self.reviewed_candidate_count = len(self.candidate_review_decisions)
        self.review_state = BeginnerArtifactState.CURRENT
        self._clear_prewrite_previews("review_completed")
        self.current_step = BeginnerFlowStep.CHECK_BEFORE_WRITE

    def clear_candidate_review(self) -> None:
        self._ensure_open()
        self.review_revision += 1
        self._clear_from_review("candidate_review_cleared")
        self.current_step = BeginnerFlowStep.REVIEW_CANDIDATE_CARDS

    def change_knowledge_selection(self, selected_count: int) -> None:
        self._ensure_open()
        self._validate_count(selected_count, "selected_count")
        if self.recognition_state is not BeginnerArtifactState.CURRENT:
            raise ValueError("recognition must be current before knowledge selection.")
        self.knowledge_selection_revision += 1
        self.selected_knowledge_point_ids = ()
        self.selected_knowledge_point_count = selected_count
        self.knowledge_selection_state = BeginnerArtifactState.CURRENT
        self._clear_from_candidates("knowledge_selection_changed")
        self.current_step = BeginnerFlowStep.REVIEW_CANDIDATE_CARDS

    def change_candidate_cards(self, candidate_count: int) -> None:
        self._ensure_open()
        self._validate_count(candidate_count, "candidate_count")
        if self.knowledge_selection_state is not BeginnerArtifactState.CURRENT:
            raise ValueError("knowledge selection must be current before candidates.")
        self.candidate_revision += 1
        self.candidate_card_previews = ()
        self.candidate_count = candidate_count
        self.candidate_cards_state = BeginnerArtifactState.CURRENT
        self._clear_from_review("candidate_cards_changed")
        self.current_step = BeginnerFlowStep.REVIEW_CANDIDATE_CARDS

    def change_review_decision(self, reviewed_candidate_count: int) -> None:
        self._ensure_open()
        self._validate_count(reviewed_candidate_count, "reviewed_candidate_count")
        if self.candidate_cards_state is not BeginnerArtifactState.CURRENT:
            raise ValueError("candidate cards must be current before review.")
        if reviewed_candidate_count > self.candidate_count:
            raise ValueError("reviewed_candidate_count cannot exceed candidate_count.")
        self.review_revision += 1
        self.reviewed_candidate_count = reviewed_candidate_count
        self.review_state = BeginnerArtifactState.CURRENT
        self._clear_prewrite_previews("review_decision_changed")
        self.current_step = BeginnerFlowStep.CHECK_BEFORE_WRITE

    def mark_prewrite_check_inspected(self) -> None:
        """Mark explanatory previews current without recording authority or consent."""

        self._ensure_open()
        if self.review_state is not BeginnerArtifactState.CURRENT:
            raise ValueError("review must be current before the pre-write check.")
        self.eligibility_state = BeginnerArtifactState.CURRENT
        self.write_plan_preview_state = BeginnerArtifactState.CURRENT
        self.final_confirmation_preview_state = BeginnerArtifactState.CURRENT
        self.last_clearing_reason = None
        self.current_step = BeginnerFlowStep.COMPLETED_NO_WRITE

    def go_back(self, target_step: BeginnerFlowStep) -> None:
        """Go to an earlier step and clear every result downstream of it."""

        self._ensure_open()
        if not isinstance(target_step, BeginnerFlowStep):
            raise ValueError("target_step must be a BeginnerFlowStep.")
        current_index = BEGINNER_FLOW_STEP_ORDER.index(self.current_step)
        target_index = BEGINNER_FLOW_STEP_ORDER.index(target_step)
        if target_index >= current_index:
            raise ValueError("go_back only accepts an earlier step.")

        if target_step is BeginnerFlowStep.SELECT_MATERIAL:
            self._clear_from_recognition("navigation_back")
        elif target_step is BeginnerFlowStep.INSPECT_RECOGNITION:
            self._clear_from_knowledge_selection("navigation_back")
        elif target_step is BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS:
            self._clear_from_candidates("navigation_back")
        elif target_step is BeginnerFlowStep.REVIEW_CANDIDATE_CARDS:
            self._clear_from_review("navigation_back")
        elif target_step is BeginnerFlowStep.CHECK_BEFORE_WRITE:
            self._clear_prewrite_previews("navigation_back")
        self.current_step = target_step

    def close(self) -> None:
        """Discard every in-memory result and make this session unusable."""

        self.current_step = BeginnerFlowStep.SELECT_MATERIAL
        self.material_text = ""
        self.material_revision = 0
        self.recognition_revision = 0
        self.knowledge_selection_revision = 0
        self.candidate_revision = 0
        self.review_revision = 0
        self.selected_knowledge_point_count = 0
        self.candidate_count = 0
        self.reviewed_candidate_count = 0
        self.recognized_knowledge_points = ()
        self.selected_knowledge_point_ids = ()
        self.candidate_card_previews = ()
        self.candidate_review_decisions.clear()
        self.recognition_state = BeginnerArtifactState.EMPTY
        self.knowledge_selection_state = BeginnerArtifactState.EMPTY
        self.candidate_cards_state = BeginnerArtifactState.EMPTY
        self.review_state = BeginnerArtifactState.EMPTY
        self.eligibility_state = BeginnerArtifactState.EMPTY
        self.write_plan_preview_state = BeginnerArtifactState.EMPTY
        self.final_confirmation_preview_state = BeginnerArtifactState.EMPTY
        self.last_clearing_reason = "session_closed"
        self.closed = True

    def to_safe_dict(self) -> dict:
        """Return structural state only; the model never stores user content."""

        return {
            "current_step": self.current_step.value,
            "closed": self.closed,
            "is_offline_read_only": self.is_offline_read_only,
            "network_allowed": self.network_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "api_key_read_allowed": self.api_key_read_allowed,
            "duplicate_check_allowed": self.duplicate_check_allowed,
            "anki_collection_access_allowed": self.anki_collection_access_allowed,
            "anki_write_allowed": self.anki_write_allowed,
            "persistent": self.persistent,
            "material_present": bool(self.material_text),
            "material_char_count": self.material_char_count,
            "material_revision": self.material_revision,
            "recognition_revision": self.recognition_revision,
            "knowledge_selection_revision": self.knowledge_selection_revision,
            "candidate_revision": self.candidate_revision,
            "review_revision": self.review_revision,
            "selected_knowledge_point_count": self.selected_knowledge_point_count,
            "candidate_count": self.candidate_count,
            "reviewed_candidate_count": self.reviewed_candidate_count,
            "recognized_knowledge_point_count": len(
                self.recognized_knowledge_points
            ),
            "candidate_review_decision_count": len(
                self.candidate_review_decisions
            ),
            "recognition_state": self.recognition_state.value,
            "knowledge_selection_state": self.knowledge_selection_state.value,
            "candidate_cards_state": self.candidate_cards_state.value,
            "review_state": self.review_state.value,
            "eligibility_state": self.eligibility_state.value,
            "write_plan_preview_state": self.write_plan_preview_state.value,
            "final_confirmation_preview_state": (
                self.final_confirmation_preview_state.value
            ),
            "last_clearing_reason": self.last_clearing_reason,
        }

    @classmethod
    def public_field_names(cls) -> tuple[str, ...]:
        """Expose the auditable stored shape without constructing a session."""

        return tuple(item.name for item in fields(cls))

    def _clear_from_recognition(self, reason: str) -> None:
        self.recognized_knowledge_points = ()
        self.recognition_state = BeginnerArtifactState.CLEARED
        self._clear_from_knowledge_selection(reason)

    def _clear_from_knowledge_selection(self, reason: str) -> None:
        self.knowledge_selection_state = BeginnerArtifactState.CLEARED
        self.selected_knowledge_point_ids = ()
        self.selected_knowledge_point_count = 0
        self._clear_from_candidates(reason)

    def _clear_from_candidates(self, reason: str) -> None:
        self.candidate_cards_state = BeginnerArtifactState.CLEARED
        self.candidate_card_previews = ()
        self.candidate_count = 0
        self._clear_from_review(reason)

    def _clear_from_review(self, reason: str) -> None:
        self.review_state = BeginnerArtifactState.CLEARED
        self.candidate_review_decisions.clear()
        self.reviewed_candidate_count = 0
        self._clear_prewrite_previews(reason)

    def _clear_prewrite_previews(self, reason: str) -> None:
        self.eligibility_state = BeginnerArtifactState.CLEARED
        self.write_plan_preview_state = BeginnerArtifactState.CLEARED
        self.final_confirmation_preview_state = BeginnerArtifactState.CLEARED
        self.last_clearing_reason = reason

    def _ensure_open(self) -> None:
        if self.closed:
            raise RuntimeError("closed beginner flow sessions cannot be reused.")

    @staticmethod
    def _validate_count(value: int, name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer.")

    @staticmethod
    def _normalize_review_decision(
        decision: Optional[BeginnerReviewDecision | str],
    ) -> Optional[BeginnerReviewDecision]:
        if decision is None:
            return None
        if isinstance(decision, BeginnerReviewDecision):
            return decision
        aliases = {
            "reviewed": BeginnerReviewDecision.LOOKS_GOOD,
            BeginnerReviewDecision.LOOKS_GOOD.value: (
                BeginnerReviewDecision.LOOKS_GOOD
            ),
            BeginnerReviewDecision.NEEDS_CHANGES.value: (
                BeginnerReviewDecision.NEEDS_CHANGES
            ),
            BeginnerReviewDecision.SKIP_FOR_NOW.value: (
                BeginnerReviewDecision.SKIP_FOR_NOW
            ),
        }
        try:
            return aliases[decision]
        except (KeyError, TypeError):
            raise ValueError("unsupported candidate review decision.") from None

    @staticmethod
    def _shorten(text: str, max_chars: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 1].rstrip() + "…"
