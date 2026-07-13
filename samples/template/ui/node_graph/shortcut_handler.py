"""Shortcut handler for keyboard operations on the node graph."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence


class ShortcutHandler:
    """Registers keyboard shortcuts on a node graph viewer.

    Shortcuts registered:
        Delete / Backspace  → delete selected nodes
        Ctrl+C              → copy selected nodes
        Ctrl+V              → paste nodes from clipboard
    """

    def __init__(self, viewer, on_delete, on_copy, on_paste):
        """Register shortcuts on a QGraphicsView.

        Args:
            viewer: NodeGraphQt NodeViewer (QGraphicsView).
            on_delete: Callable with no args → delete selected.
            on_copy: Callable with no args → copy selected.
            on_paste: Callable with no args → paste.
        """
        QShortcut(QKeySequence(Qt.Key_Delete), viewer, on_delete)
        QShortcut(QKeySequence(Qt.Key_Backspace), viewer, on_delete)
        QShortcut(QKeySequence.StandardKey.Copy, viewer, on_copy)
        QShortcut(QKeySequence.StandardKey.Paste, viewer, on_paste)
