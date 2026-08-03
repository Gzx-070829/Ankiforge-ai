"""Persistence adapter for strictly non-sensitive workbench window state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from ..workbench.window_state import WorkbenchWindowState


MAX_WINDOW_STATE_FILE_BYTES = 16 * 1024
_WINDOW_STATE_FILENAME = "window_state.json"
_TEMP_FILENAME = ".window_state.json.tmp"


def default_window_state_path() -> Path:
    """Return Anki's preserved add-on ``user_files`` state path."""

    addon_root = Path(__file__).resolve().parents[1]
    return addon_root / "user_files" / _WINDOW_STATE_FILENAME


class WindowStateAdapter:
    """Load and atomically save one validated window-state value."""

    def __init__(self, path: Optional[Path] = None):
        resolved = (
            Path(path)
            if path is not None
            else default_window_state_path()
        )
        if (
            resolved.name != _WINDOW_STATE_FILENAME
            or resolved.parent.name != "user_files"
        ):
            raise ValueError(
                "window state path must end in user_files/window_state.json"
            )
        self.path = resolved

    def load(self) -> WorkbenchWindowState:
        try:
            if (
                not self.path.exists()
                or not self.path.is_file()
                or self.path.is_symlink()
                or self.path.parent.is_symlink()
            ):
                return WorkbenchWindowState.defaults()
            size = self.path.stat().st_size
            if size < 2 or size > MAX_WINDOW_STATE_FILE_BYTES:
                return WorkbenchWindowState.defaults()
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return WorkbenchWindowState.from_mapping(payload)
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
            TypeError,
        ):
            return WorkbenchWindowState.defaults()

    def save(self, state: WorkbenchWindowState) -> None:
        if not isinstance(state, WorkbenchWindowState):
            raise TypeError("state must be WorkbenchWindowState")
        payload = state.to_safe_dict()
        WorkbenchWindowState.from_mapping(payload)
        content = (
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if len(content) > MAX_WINDOW_STATE_FILE_BYTES:
            raise ValueError("window state payload is too large")

        directory = self.path.parent
        if self.path.is_symlink() or (
            directory.exists() and directory.is_symlink()
        ):
            raise ValueError("window state path must not use a symlink")
        directory.mkdir(parents=True, exist_ok=True)
        temporary_path = directory / _TEMP_FILENAME
        if temporary_path.is_symlink():
            raise ValueError("temporary window state path must not be a symlink")
        try:
            if temporary_path.exists():
                temporary_path.unlink()
            temporary_path.write_bytes(content)
            os.replace(str(temporary_path), str(self.path))
        finally:
            if temporary_path.exists() and not temporary_path.is_symlink():
                temporary_path.unlink()
