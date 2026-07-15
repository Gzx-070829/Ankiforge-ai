"""Validated, non-sensitive settings for card generation."""

from dataclasses import dataclass
from typing import Mapping, Optional


CARD_MODES = (
    "concept",
    "definition",
    "exam",
    "quick_review",
    "compare_contrast",
    "process_steps",
    "formula_rule",
    "mistake_trap",
    "cloze_candidate",
)
CARD_COUNTS = ("auto", "fewer", "balanced", "more")
ANSWER_LENGTHS = ("short", "medium")
OUTPUT_LANGUAGES = ("auto", "zh", "en")


@dataclass(frozen=True, repr=False)
class CardModeProfile:
    mode_id: str
    display_name_zh: str
    display_name_en: str
    description_zh: str
    description_en: str
    prompt_guidance: str
    default_answer_length: str
    default_card_density: str
    quality_priorities: tuple[str, ...]
    selectable: bool = True

    def __repr__(self) -> str:
        return (
            "CardModeProfile("
            f"mode_id={self.mode_id!r}, "
            f"quality_priority_count={len(self.quality_priorities)})"
        )


_CARD_MODE_PROFILES = (
    CardModeProfile(
        mode_id="concept",
        display_name_zh="概念理解",
        display_name_en="Concept",
        description_zh="理解概念、因果、区别和意义",
        description_en="Understand concepts, causes, differences, and significance",
        prompt_guidance=(
            "Focus on concept understanding, cause and effect, important differences, "
            "and why the idea matters."
        ),
        default_answer_length="short",
        default_card_density="balanced",
        quality_priorities=("atomic", "specific", "explanatory"),
    ),
    CardModeProfile(
        mode_id="definition",
        display_name_zh="术语定义",
        display_name_en="Definition",
        description_zh="记忆术语、定义、关键特征和必要例子",
        description_en="Learn terms, definitions, key traits, and essential examples",
        prompt_guidance=(
            "Focus on the term, its precise definition, key characteristics, and only "
            "an essential example when it improves the definition."
        ),
        default_answer_length="short",
        default_card_density="balanced",
        quality_priorities=("precise", "definitional", "concise"),
    ),
    CardModeProfile(
        mode_id="exam",
        display_name_zh="考试复习",
        display_name_en="Exam",
        description_zh="用考题式正面和简洁标准答题点复习",
        description_en="Review with exam-style questions and concise answer points",
        prompt_guidance=(
            "Write an exam-style question and a concise model answer containing the "
            "standard scoring points, without essay-like filler."
        ),
        default_answer_length="short",
        default_card_density="balanced",
        quality_priorities=("testable", "scoring-points", "direct"),
    ),
    CardModeProfile(
        mode_id="quick_review",
        display_name_zh="快速记忆",
        display_name_en="Quick review",
        description_zh="短问短答，一卡一事实",
        description_en="Short question, short answer, one fact per card",
        prompt_guidance=(
            "Use a very short question and answer for quick recall: one fact per card "
            "and no extra explanation."
        ),
        default_answer_length="short",
        default_card_density="more",
        quality_priorities=("one-fact", "brief", "fast-recall"),
    ),
    CardModeProfile(
        mode_id="compare_contrast",
        display_name_zh="对比辨析",
        display_name_en="Compare & contrast",
        description_zh="在同一维度区分两个容易混淆的概念",
        description_en="Distinguish two concepts on the same meaningful dimension",
        prompt_guidance=(
            "Name both sides explicitly and compare them on the same meaningful "
            "dimension; make the distinction useful for recall."
        ),
        default_answer_length="short",
        default_card_density="fewer",
        quality_priorities=("two-sided", "same-dimension", "distinctive"),
    ),
    CardModeProfile(
        mode_id="process_steps",
        display_name_zh="流程步骤",
        display_name_en="Process steps",
        description_zh="记忆步骤、流程与先后顺序",
        description_en="Learn steps, processes, and their order",
        prompt_guidance=(
            "Ask for one bounded process and preserve explicit order, transitions, "
            "and only the steps supported by the material."
        ),
        default_answer_length="medium",
        default_card_density="fewer",
        quality_priorities=("ordered", "complete", "concise"),
    ),
    CardModeProfile(
        mode_id="formula_rule",
        display_name_zh="公式规则",
        display_name_en="Formula or rule",
        description_zh="记忆公式、规则、变量和适用条件",
        description_en="Learn a formula or rule, its variables, and conditions",
        prompt_guidance=(
            "State the formula or rule precisely, define essential variables, and "
            "include its applicable condition without adding a long derivation."
        ),
        default_answer_length="short",
        default_card_density="fewer",
        quality_priorities=("correct-form", "variables", "condition"),
    ),
    CardModeProfile(
        mode_id="mistake_trap",
        display_name_zh="易错陷阱",
        display_name_en="Mistake trap",
        description_zh="识别常见误区并给出简洁纠正",
        description_en="Recognize a common misconception and its correction",
        prompt_guidance=(
            "Focus on one misconception or easily confused point that is explicitly "
            "grounded in the material, then give its concise correction."
        ),
        default_answer_length="short",
        default_card_density="balanced",
        quality_priorities=("misconception", "correction", "grounded"),
    ),
    CardModeProfile(
        mode_id="cloze_candidate",
        display_name_zh="填空候选",
        display_name_en="Cloze candidate",
        description_zh="仅在兼容笔记类型下使用简单、安全的填空",
        description_en="Use a simple cloze only with a compatible note type",
        prompt_guidance=(
            "Create at most one simple, non-nested cloze deletion with enough context; "
            "treat it as unsupported unless note-type compatibility is confirmed."
        ),
        default_answer_length="short",
        default_card_density="fewer",
        quality_priorities=("valid-syntax", "single-deletion", "compatible"),
        selectable=False,
    ),
)
_PROFILE_BY_ID = {profile.mode_id: profile for profile in _CARD_MODE_PROFILES}


@dataclass(frozen=True)
class GenerationSettings:
    card_mode: str = "concept"
    card_count: str = "balanced"
    answer_length: str = "short"
    language: str = "auto"

    def __post_init__(self) -> None:
        _validate_choice(self.card_mode, CARD_MODES, "card_mode")
        _validate_choice(self.card_count, CARD_COUNTS, "card_count")
        _validate_choice(self.answer_length, ANSWER_LENGTHS, "answer_length")
        _validate_choice(self.language, OUTPUT_LANGUAGES, "language")

    def to_safe_dict(self) -> dict[str, str]:
        return {
            "card_mode": self.card_mode,
            "card_count": self.card_count,
            "answer_length": self.answer_length,
            "language": self.language,
        }


def all_card_mode_profiles() -> tuple[CardModeProfile, ...]:
    return _CARD_MODE_PROFILES


def selectable_card_mode_profiles() -> tuple[CardModeProfile, ...]:
    """Return modes that are safe to expose in the current Basic-card UI."""

    return tuple(profile for profile in _CARD_MODE_PROFILES if profile.selectable)


def get_card_mode_profile(mode_id: str) -> CardModeProfile:
    try:
        return _PROFILE_BY_ID[mode_id]
    except (KeyError, TypeError):
        raise ValueError(f"unsupported card_mode: {mode_id!r}") from None


def coerce_generation_settings(
    value: Optional[GenerationSettings | Mapping[str, str]],
) -> GenerationSettings:
    if value is None:
        return GenerationSettings()
    if isinstance(value, GenerationSettings):
        return value
    if isinstance(value, Mapping):
        return GenerationSettings(**dict(value))
    raise ValueError("settings must be GenerationSettings, a mapping, or None.")


def card_limit_for_settings(settings: Optional[GenerationSettings] = None) -> int:
    resolved = coerce_generation_settings(settings)
    return {"auto": 5, "fewer": 3, "balanced": 5, "more": 8}[
        resolved.card_count
    ]


def _validate_choice(value: str, choices: tuple[str, ...], name: str) -> None:
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{name} must be one of: {', '.join(choices)}.")
