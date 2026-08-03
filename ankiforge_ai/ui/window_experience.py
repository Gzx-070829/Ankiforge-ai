"""Small testable helpers for the native workbench window experience."""

from __future__ import annotations

import base64
from typing import Any

from ..workbench.window_state import WorkbenchWindowState


def configure_workbench_window(dialog: Any, qt_namespace: Any) -> None:
    """Apply ordinary top-level controls and delete-on-close ownership."""

    window_type = qt_namespace.WindowType
    for flag in (
        window_type.Window,
        window_type.WindowTitleHint,
        window_type.WindowSystemMenuHint,
        window_type.WindowMinMaxButtonsHint,
        window_type.WindowCloseButtonHint,
    ):
        dialog.setWindowFlag(flag, True)
    dialog.setAttribute(
        qt_namespace.WidgetAttribute.WA_DeleteOnClose,
        True,
    )


def capture_window_state(dialog: Any) -> WorkbenchWindowState:
    """Capture only Qt geometry bytes and the maximized flag."""

    geometry = base64.b64encode(bytes(dialog.saveGeometry())).decode("ascii")
    return WorkbenchWindowState(
        geometry=geometry,
        maximized=bool(dialog.isMaximized()),
    )


def restore_window_geometry(
    dialog: Any,
    state: WorkbenchWindowState,
    byte_array_type: Any,
    window_type: Any,
) -> bool:
    """Restore validated geometry without showing the window prematurely."""

    if not isinstance(state, WorkbenchWindowState) or not state.geometry:
        return False
    decoded = base64.b64decode(state.geometry, validate=True)
    if not dialog.restoreGeometry(byte_array_type(decoded)):
        return False
    if state.maximized:
        dialog.setWindowState(
            dialog.windowState() | window_type.WindowMaximized
        )
    return True


def focus_when_ready(timer_type: Any, target: Any) -> None:
    """Focus the material editor after Qt has entered its event loop."""

    timer_type.singleShot(0, target.setFocus)
