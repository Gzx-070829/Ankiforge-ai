"""Legacy preference compatibility for AnkiForge AI.

The active UI keeps Provider credentials in memory for the current window and
does not use this module to persist them.  This loader remains only for legacy
non-sensitive preferences; sensitive field names are scrubbed while reading
old files and are rejected when callers attempt to save them.
"""

import json
import os
import re
import unicodedata
from collections.abc import Mapping
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

_SENSITIVE_FIELD_MARKERS = (
    "apikey",
    "token",
    "secret",
    "bearer",
    "password",
    "authorization",
)


class SensitiveConfigFieldError(ValueError):
    """Raised when legacy preference persistence receives credential fields."""


def config_path() -> str:
    return os.path.join(os.path.dirname(__file__), "config.json")


def load_config(path: Optional[str] = None) -> Dict:
    """Load legacy non-sensitive preferences over stable defaults.

    Any credential-like keys in an existing file are ignored for backward
    compatibility.  The returned empty ``api_key`` is a runtime-only sentinel
    for old callers and is never persisted by :func:`save_config`.
    """
    target = path or config_path()
    data = {}
    try:
        with open(target, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data = _scrub_sensitive_fields(loaded)
    except (OSError, ValueError):
        data = {}

    config = dict(DEFAULT_CONFIG)
    config.update(data)
    config["api_key"] = ""
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
    """Persist legacy preferences only when no sensitive field is present.

    Credential-shaped fields are refused even when empty so callers cannot
    mistake silent discarding for successful persistence.
    """
    if not isinstance(config, Mapping):
        raise TypeError("legacy config must be a mapping")
    _assert_no_sensitive_fields(config)

    target = path or config_path()
    normalized = dict(load_config(path))
    normalized.update(config)
    normalized.pop("api_key", None)
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
    _assert_no_sensitive_fields(normalized)
    serialized = json.dumps(normalized, ensure_ascii=False, indent=4) + "\n"
    with open(target, "w", encoding="utf-8") as f:
        f.write(serialized)


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


def _compact_field_name(field_name: str) -> str:
    normalized = unicodedata.normalize("NFKC", field_name).casefold()
    return re.sub(r"[^a-z0-9]", "", normalized)


def _is_sensitive_field_name(field_name: str) -> bool:
    compact = _compact_field_name(field_name)
    return any(marker in compact for marker in _SENSITIVE_FIELD_MARKERS)


def _assert_no_sensitive_fields(value, seen=None) -> None:
    if seen is None:
        seen = set()

    if isinstance(value, Mapping):
        object_id = id(value)
        if object_id in seen:
            return
        seen.add(object_id)
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("legacy config field names must be strings")
            if _is_sensitive_field_name(key):
                raise SensitiveConfigFieldError(
                    "Refusing to persist sensitive fields in legacy configuration."
                )
            _assert_no_sensitive_fields(item, seen)
        return

    if isinstance(value, (list, tuple)):
        object_id = id(value)
        if object_id in seen:
            return
        seen.add(object_id)
        for item in value:
            _assert_no_sensitive_fields(item, seen)


def _scrub_sensitive_fields(value):
    if isinstance(value, Mapping):
        return {
            key: _scrub_sensitive_fields(item)
            for key, item in value.items()
            if isinstance(key, str) and not _is_sensitive_field_name(key)
        }
    if isinstance(value, list):
        return [_scrub_sensitive_fields(item) for item in value]
    return value
