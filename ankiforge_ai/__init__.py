"""
AnkiForge AI - entry point.

Anki loads this file when the add-on starts. It just registers a menu item
under Tools; all real logic lives in the submodules so this file stays
trivial to read.
"""

from aqt import mw
from aqt.qt import QAction

from .ui.main_dialog import MainDialog

_dialog_instance = None


def _open_main_dialog():
    global _dialog_instance
    _dialog_instance = MainDialog(mw)
    _dialog_instance.exec()


_action = QAction("AnkiForge AI", mw)
_action.triggered.connect(_open_main_dialog)
mw.form.menuTools.addAction(_action)
