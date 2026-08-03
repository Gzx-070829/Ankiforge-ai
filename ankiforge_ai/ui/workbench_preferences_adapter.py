"""Small file adapter for the workbench's non-sensitive preferences only."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from ..workbench.preferences import WorkbenchPreferences


MAX_PREFERENCES_FILE_BYTES = 16 * 1024
_PREFERENCES_FILENAME = "preferences.json"
_TEMP_FILENAME = ".preferences.json.tmp"


def default_preferences_path() -> Path:
    """Return Anki's preserved add-on ``user_files`` preference path."""

    addon_root = Path(__file__).resolve().parents[1]
    return addon_root / "user_files" / _PREFERENCES_FILENAME


class WorkbenchPreferencesAdapter:
    """Load and atomically save one strictly validated preference value."""

    def __init__(self, path: Optional[Path] = None):
        resolved = Path(path) if path is not None else default_preferences_path()
        if resolved.name != _PREFERENCES_FILENAME or resolved.parent.name != "user_files":
            raise ValueError("preferences path must end in user_files/preferences.json")
        self.path = resolved

    def load(self) -> WorkbenchPreferences:
        try:
            if not self.path.exists() or not self.path.is_file() or self.path.is_symlink():
                return WorkbenchPreferences.defaults()
            size = self.path.stat().st_size
            if size < 2 or size > MAX_PREFERENCES_FILE_BYTES:
                return WorkbenchPreferences.defaults()
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return WorkbenchPreferences.from_mapping(payload)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
            return WorkbenchPreferences.defaults()

    def save(self, preferences: WorkbenchPreferences) -> None:
        if not isinstance(preferences, WorkbenchPreferences):
            raise TypeError("preferences must be WorkbenchPreferences")
        payload = preferences.to_safe_dict()
        # Revalidate at the final storage boundary even for an existing value.
        WorkbenchPreferences.from_mapping(payload)
        content = (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if len(content) > MAX_PREFERENCES_FILE_BYTES:
            raise ValueError("preference payload is too large")

        directory = self.path.parent
        if self.path.is_symlink() or (directory.exists() and directory.is_symlink()):
            raise ValueError("preference path must not use a symlink")
        directory.mkdir(parents=True, exist_ok=True)
        temporary_path = directory / _TEMP_FILENAME
        try:
            if temporary_path.exists():
                temporary_path.unlink()
            temporary_path.write_bytes(content)
            os.replace(str(temporary_path), str(self.path))
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
