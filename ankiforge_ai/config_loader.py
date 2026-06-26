"""Configuration loading for AnkiForge AI.

The v0.1.2 config intentionally contains no API key. It only selects the
local mock provider and reserves non-secret fields for future providers.
"""

import json
import os
from typing import Dict, Optional

from .ai.providers.base import AIProviderConfig

DEFAULT_CONFIG = {
    "ai_provider": "mock",
    "model": "mock-v0.1.2",
    "api_base_url": "",
    "max_cards_per_chunk": 3,
    "default_deck": "AnkiForge::Inbox",
    "default_note_type": "AnkiForge Basic",
    "obsidian_vault_path": "",
}


def config_path() -> str:
    return os.path.join(os.path.dirname(__file__), "config.json")


def load_config(path: Optional[str] = None) -> Dict:
    """Load config.json and merge it over stable defaults."""
    target = path or config_path()
    data = {}
    try:
        with open(target, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data = loaded
    except (OSError, ValueError):
        data = {}

    config = dict(DEFAULT_CONFIG)
    config.update(data)
    config["max_cards_per_chunk"] = _normalize_positive_int(
        config.get("max_cards_per_chunk"),
        DEFAULT_CONFIG["max_cards_per_chunk"],
    )
    return config


def load_provider_config(path: Optional[str] = None) -> AIProviderConfig:
    config = load_config(path)
    return AIProviderConfig(
        ai_provider=str(config.get("ai_provider") or "mock"),
        model=str(config.get("model") or "mock-v0.1.2"),
        api_base_url=str(config.get("api_base_url") or ""),
        max_cards_per_chunk=config["max_cards_per_chunk"],
    )


def default_deck_name(path: Optional[str] = None) -> str:
    config = load_config(path)
    return str(config.get("default_deck") or DEFAULT_CONFIG["default_deck"])


def _normalize_positive_int(value, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return number if number > 0 else fallback
