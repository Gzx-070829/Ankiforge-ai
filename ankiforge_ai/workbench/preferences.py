"""Strict non-sensitive preferences for the public workbench.

This value intentionally cannot represent credentials, endpoints, study
material, source paths, review state, or write history. Those values therefore
cannot cross the preference storage boundary by accident.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Mapping

from ..pipeline.generation_settings import (
    ANSWER_LENGTHS,
    CARD_COUNTS,
    OUTPUT_LANGUAGES,
    selectable_card_mode_profiles,
)


PREFERENCES_SCHEMA_VERSION = 1
_ALLOWED_FIELDS = frozenset(
    {
        "schema_version",
        "ui_language",
        "provider_name",
        "model_name",
        "card_mode",
        "card_count",
        "answer_length",
        "output_language",
        "intelligence_level",
    }
)
_UI_LANGUAGES = frozenset({"zh", "en"})
_PROVIDER_NAMES = frozenset({"DeepSeek", "OpenAI", "OpenAI-compatible"})
_PUBLIC_CARD_MODES = frozenset(
    profile.mode_id for profile in selectable_card_mode_profiles()
)
_INTELLIGENCE_LEVELS = frozenset({"fast", "standard", "deep"})
_SAFE_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SECRET_SHAPED_VALUE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|bearer\s+|github_pat_|gh[pousr]_)",
    re.IGNORECASE,
)


@dataclass(frozen=True, repr=False)
class WorkbenchPreferences:
    """A versioned allowlist of low-risk convenience choices."""

    schema_version: int = PREFERENCES_SCHEMA_VERSION
    ui_language: str = "zh"
    provider_name: str = "DeepSeek"
    model_name: str = "deepseek-v4-flash"
    card_mode: str = "concept"
    card_count: str = "balanced"
    answer_length: str = "short"
    output_language: str = "auto"
    intelligence_level: str = "standard"

    def __post_init__(self) -> None:
        if self.schema_version != PREFERENCES_SCHEMA_VERSION:
            raise ValueError("unsupported workbench preference schema")
        _require_choice(self.ui_language, _UI_LANGUAGES, "ui language")
        _require_choice(self.provider_name, _PROVIDER_NAMES, "provider")
        _require_model_name(self.model_name)
        _require_choice(self.card_mode, _PUBLIC_CARD_MODES, "card mode")
        _require_choice(self.card_count, frozenset(CARD_COUNTS), "card count")
        _require_choice(
            self.answer_length,
            frozenset(ANSWER_LENGTHS),
            "answer length",
        )
        _require_choice(
            self.output_language,
            frozenset(OUTPUT_LANGUAGES),
            "output language",
        )
        _require_choice(
            self.intelligence_level,
            _INTELLIGENCE_LEVELS,
            "intelligence level",
        )

    @classmethod
    def defaults(cls) -> "WorkbenchPreferences":
        return cls()

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "WorkbenchPreferences":
        if not isinstance(value, Mapping):
            raise ValueError("workbench preferences must be an object")
        if set(value) != _ALLOWED_FIELDS:
            raise ValueError("workbench preferences contain unsupported fields")
        return cls(
            schema_version=value["schema_version"],
            ui_language=value["ui_language"],
            provider_name=value["provider_name"],
            model_name=value["model_name"],
            card_mode=value["card_mode"],
            card_count=value["card_count"],
            answer_length=value["answer_length"],
            output_language=value["output_language"],
            intelligence_level=value["intelligence_level"],
        )

    def with_updates(self, **changes) -> "WorkbenchPreferences":
        if not changes or not set(changes).issubset(_ALLOWED_FIELDS - {"schema_version"}):
            raise ValueError("preference updates must use supported fields")
        return replace(self, **changes)

    def to_safe_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "ui_language": self.ui_language,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "card_mode": self.card_mode,
            "card_count": self.card_count,
            "answer_length": self.answer_length,
            "output_language": self.output_language,
            "intelligence_level": self.intelligence_level,
        }

    def __repr__(self) -> str:
        return (
            "WorkbenchPreferences("
            f"schema_version={self.schema_version}, "
            f"ui_language={self.ui_language!r}, "
            f"provider_name={self.provider_name!r}, "
            f"card_mode={self.card_mode!r}, "
            f"card_count={self.card_count!r}, "
            f"answer_length={self.answer_length!r}, "
            f"output_language={self.output_language!r}, "
            f"intelligence_level={self.intelligence_level!r})"
        )


def _require_choice(value: object, allowed: frozenset, label: str) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"unsupported {label}")


def _require_model_name(value: object) -> None:
    if (
        not isinstance(value, str)
        or not _SAFE_MODEL_NAME.fullmatch(value)
        or "://" in value
        or _SECRET_SHAPED_VALUE.search(value)
    ):
        raise ValueError("model name must be a bounded non-sensitive identifier")
