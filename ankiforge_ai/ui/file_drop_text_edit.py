"""Small QTextEdit extension that forwards dropped local files."""

from __future__ import annotations

from collections.abc import Callable

from aqt.qt import QTextEdit


class FileDropTextEdit(QTextEdit):
    """Keep normal text drops while routing local file URLs to a callback."""

    def __init__(self, parent=None, *, files_dropped: Callable | None = None):
        super().__init__(parent)
        self._files_dropped = files_dropped
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if self._local_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._local_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        paths = self._local_paths(event.mimeData())
        if not paths:
            super().dropEvent(event)
            return
        if self._files_dropped is not None:
            self._files_dropped(paths)
        event.acceptProposedAction()

    @staticmethod
    def _local_paths(mime_data) -> tuple[str, ...]:
        if not mime_data.hasUrls():
            return ()
        return tuple(
            url.toLocalFile()
            for url in mime_data.urls()
            if url.isLocalFile() and url.toLocalFile()
        )
