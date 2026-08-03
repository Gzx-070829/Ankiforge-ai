"""
AnkiForge AI - add-on entry point.

Anki imports this module when the add-on starts. The registration code is
kept behind a small function so pure Python tests can import submodules on a
machine that does not have Anki's `aqt` package installed.
"""

__version__ = "0.15.0"

_dialog_instance = None
_menu_action = globals().get("_menu_action")


def _clear_main_dialog(dialog):
    """Release the singleton only when the matching Qt object is destroyed."""
    global _dialog_instance

    if _dialog_instance is dialog:
        _dialog_instance = None


def _show_main_dialog(parent, dialog_factory):
    """Show or focus the one modeless AnkiForge workbench window."""
    global _dialog_instance

    dialog = _dialog_instance
    if dialog is None:
        dialog = dialog_factory(parent)
        dialog.destroyed.connect(
            lambda *_args, current=dialog: _clear_main_dialog(current)
        )
        _dialog_instance = dialog
        dialog.show()
    elif dialog.isMinimized():
        dialog.showNormal()
    else:
        dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog


def _open_from_anki():
    """Open the workbench from any registered Anki entry point."""

    from aqt import mw

    from .ui.main_dialog import MainDialog

    return _show_main_dialog(mw, MainDialog)


def _register_menu_action():
    global _menu_action

    if _menu_action is not None:
        return _menu_action

    try:
        from aqt import mw
        from aqt.qt import QAction
    except ImportError:
        return

    action = QAction("AnkiForge AI", mw)
    action.setShortcut("Ctrl+Alt+F")
    action.triggered.connect(_open_from_anki)
    mw.form.menuTools.addAction(action)
    _menu_action = action
    return action


def _register_home_entry():
    """Add a deck-browser launcher when the official hooks are available."""

    try:
        from aqt import gui_hooks
    except ImportError:
        return False

    from .ui.anki_entrypoints import register_home_entry

    return register_home_entry(gui_hooks, _open_from_anki)


_register_menu_action()
_register_home_entry()
