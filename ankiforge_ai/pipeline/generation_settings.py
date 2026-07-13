"""Validated, non-sensitive settings for card generation."""

from dataclasses import dataclass
from typing import Mapping, Optional


CARD_MODES = ("concept", "definition", "exam", "quick_review")
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
