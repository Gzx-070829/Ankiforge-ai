"""
AnkiForge AI - add-on entry point.

Anki imports this module when the add-on starts. The registration code is
kept behind a small function so pure Python tests can import submodules on a
machine that does not have Anki's `aqt` package installed.
"""

__version__ = "0.2.2"

_dialog_instance = None


def _register_menu_action():
    try:
        from aqt import mw
        from aqt.qt import QAction
    except ImportError:
        return

    from .ui.main_dialog import MainDialog

    def _open_main_dialog():
        global _dialog_instance
        _dialog_instance = MainDialog(mw)
        _dialog_instance.exec()

    action = QAction("AnkiForge AI", mw)
    action.triggered.connect(_open_main_dialog)
    mw.form.menuTools.addAction(action)


_register_menu_action()
