"""Configuration loading for AnkiForge AI."""

import json
import os
from typing import Dict, Optional

from .ai.providers.base import AIProviderConfig

DEFAULT_CONFIG = {
    "ai_provider": "mock",
    "model": "mock-v0.2",
    "api_base_url": "",
    "api_key": "",
    "max_cards_per_chunk": 3,
    "timeout_seconds": 60,
    "temperature": 0.2,
    "default_deck": "AnkiForge::Inbox",
    "default_note_type": "AnkiForge Basic",
    "obsidian_vault_path": "",
}

PROVIDER_PRESETS = {
    "mock": {
        "model": "mock-v0.2",
        "api_base_url": "",
    },
    "deepseek": {
        "model": "deepseek-chat",
        "api_base_url": "https://api.deepseek.com",
    },
    "openai_compatible": {
        "model": "",
        "api_base_url": "",
    },
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
    config["timeout_seconds"] = _normalize_positive_int(
        config.get("timeout_seconds"),
        DEFAULT_CONFIG["timeout_seconds"],
    )
    config["temperature"] = _normalize_float(
        config.get("temperature"),
        DEFAULT_CONFIG["temperature"],
    )
    _apply_provider_defaults(config)
    return config


def load_provider_config(path: Optional[str] = None) -> AIProviderConfig:
    config = load_config(path)
    return AIProviderConfig(
        ai_provider=str(config.get("ai_provider") or "mock"),
        model=str(config.get("model") or ""),
        api_base_url=str(config.get("api_base_url") or ""),
        api_key=str(config.get("api_key") or ""),
        max_cards_per_chunk=config["max_cards_per_chunk"],
        timeout_seconds=config["timeout_seconds"],
        temperature=config["temperature"],
    )


def save_config(config: Dict, path: Optional[str] = None) -> None:
    """Persist config JSON. API keys are user-local and never hard-coded."""
    target = path or config_path()
    normalized = dict(load_config(path))
    normalized.update(config)
    normalized["max_cards_per_chunk"] = _normalize_positive_int(
        normalized.get("max_cards_per_chunk"),
        DEFAULT_CONFIG["max_cards_per_chunk"],
    )
    normalized["timeout_seconds"] = _normalize_positive_int(
        normalized.get("timeout_seconds"),
        DEFAULT_CONFIG["timeout_seconds"],
    )
    normalized["temperature"] = _normalize_float(
        normalized.get("temperature"),
        DEFAULT_CONFIG["temperature"],
    )
    with open(target, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=4)
        f.write("\n")


def default_deck_name(path: Optional[str] = None) -> str:
    config = load_config(path)
    return str(config.get("default_deck") or DEFAULT_CONFIG["default_deck"])


def _normalize_positive_int(value, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return number if number > 0 else fallback


def _normalize_float(value, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if number >= 0 else fallback


def _apply_provider_defaults(config: Dict) -> None:
    provider = str(config.get("ai_provider") or "mock").strip().lower()
    config["ai_provider"] = provider
    preset = PROVIDER_PRESETS.get(provider)
    if not preset:
        return

    model = str(config.get("model") or "").strip()
    if not model or (provider != "mock" and model.startswith("mock-")):
        config["model"] = preset["model"]

    api_base_url = str(config.get("api_base_url") or "").strip()
    if not api_base_url and preset["api_base_url"]:
        config["api_base_url"] = preset["api_base_url"]
