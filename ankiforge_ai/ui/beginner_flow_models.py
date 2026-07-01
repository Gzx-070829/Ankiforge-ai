"""Pure-Python state and copy models for the beginner read-only walkthrough."""

from dataclasses import dataclass, field, fields
from enum import Enum
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
            description="查看材料预览，理解未来识别结果会如何呈现，再继续。",
            primary_action="查看识别结果",
            empty_state="尚无材料预览。请先输入学习材料。",
        ),
        BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS: BeginnerStepCopy(
            title="选择要制卡的知识点",
            description="了解未来如何从识别结果中挑选值得制卡的知识点。",
            primary_action="确认知识点选择",
            empty_state="本次说明尚未产生知识点选择。",
        ),
        BeginnerFlowStep.REVIEW_CANDIDATE_CARDS: BeginnerStepCopy(
            title="审核候选卡",
            description="了解未来如何检查候选卡的问答、来源和质量提示。",
            primary_action="开始人工审核",
            empty_state="本次说明尚未产生候选卡或审核结果。",
        ),
        BeginnerFlowStep.CHECK_BEFORE_WRITE: BeginnerStepCopy(
            title="查看距离真正写入还缺哪些条件",
            description="查看未来写入前仍需完成的检查；这里仅解释条件，不授予权限。",
            primary_action="查看尚未满足的条件",
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
            "本步骤只展示材料预览，尚未分析或识别真实知识点。"
        ),
        BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS: (
            "本步骤只提供流程说明，尚未产生知识点选择。"
        ),
        BeginnerFlowStep.REVIEW_CANDIDATE_CARDS: (
            "本步骤只提供流程说明，尚未产生候选卡或审核结果。"
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


@dataclass
class BeginnerFlowSession:
    """In-memory navigation state for one non-persistent walkthrough."""

    current_step: BeginnerFlowStep = BeginnerFlowStep.SELECT_MATERIAL
    material_text: str = field(default="", repr=False)
    material_revision: int = 0
    knowledge_selection_revision: int = 0
    candidate_revision: int = 0
    review_revision: int = 0
    selected_knowledge_point_count: int = 0
    candidate_count: int = 0
    reviewed_candidate_count: int = 0
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
        self.recognition_state = BeginnerArtifactState.CLEARED
        self._clear_from_knowledge_selection("material_cleared")

    def select_material(self) -> None:
        """Confirm that non-empty in-memory material may be previewed."""

        self._ensure_open()
        if not self.material_text.strip():
            raise ValueError("material text must not be empty.")
        self.recognition_state = BeginnerArtifactState.EMPTY
        self.current_step = BeginnerFlowStep.INSPECT_RECOGNITION

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
        if self.material_revision == 0:
            raise ValueError("material must be selected before recognition is inspected.")
        self.recognition_state = BeginnerArtifactState.CURRENT
        self.current_step = BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS

    def change_knowledge_selection(self, selected_count: int) -> None:
        self._ensure_open()
        self._validate_count(selected_count, "selected_count")
        if self.recognition_state is not BeginnerArtifactState.CURRENT:
            raise ValueError("recognition must be current before knowledge selection.")
        self.knowledge_selection_revision += 1
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
        self.knowledge_selection_revision = 0
        self.candidate_revision = 0
        self.review_revision = 0
        self.selected_knowledge_point_count = 0
        self.candidate_count = 0
        self.reviewed_candidate_count = 0
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
            "knowledge_selection_revision": self.knowledge_selection_revision,
            "candidate_revision": self.candidate_revision,
            "review_revision": self.review_revision,
            "selected_knowledge_point_count": self.selected_knowledge_point_count,
            "candidate_count": self.candidate_count,
            "reviewed_candidate_count": self.reviewed_candidate_count,
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
        self.recognition_state = BeginnerArtifactState.CLEARED
        self._clear_from_knowledge_selection(reason)

    def _clear_from_knowledge_selection(self, reason: str) -> None:
        self.knowledge_selection_state = BeginnerArtifactState.CLEARED
        self.selected_knowledge_point_count = 0
        self._clear_from_candidates(reason)

    def _clear_from_candidates(self, reason: str) -> None:
        self.candidate_cards_state = BeginnerArtifactState.CLEARED
        self.candidate_count = 0
        self._clear_from_review(reason)

    def _clear_from_review(self, reason: str) -> None:
        self.review_state = BeginnerArtifactState.CLEARED
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
