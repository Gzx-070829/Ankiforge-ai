"""
AnkiForge AI - add-on entry point.

Anki imports this module when the add-on starts. The registration code is
kept behind a small function so pure Python tests can import submodules on a
machine that does not have Anki's `aqt` package installed.
"""

__version__ = "0.13.2"

_dialog_instance = None
_menu_action = globals().get("_menu_action")


def _open_main_dialog(parent, dialog_factory):
    """Run one main dialog and release all session state when it exits."""
    global _dialog_instance

    dialog = dialog_factory(parent)
    _dialog_instance = dialog
    try:
        return dialog.exec()
    finally:
        try:
            teardown_session = getattr(dialog, "_teardown_session", None)
            if callable(teardown_session):
                teardown_session()
        finally:
            if _dialog_instance is dialog:
                _dialog_instance = None
            delete_later = getattr(dialog, "deleteLater", None)
            if callable(delete_later):
                delete_later()


def _register_menu_action():
    global _menu_action

    if _menu_action is not None:
        return _menu_action

    try:
        from aqt import mw
        from aqt.qt import QAction
    except ImportError:
        return

    from .ui.main_dialog import MainDialog

    def open_main_dialog():
        _open_main_dialog(mw, MainDialog)

    action = QAction("AnkiForge AI", mw)
    action.triggered.connect(open_main_dialog)
    mw.form.menuTools.addAction(action)
    _menu_action = action
    return action


_register_menu_action()
