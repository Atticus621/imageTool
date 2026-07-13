from __future__ import annotations
from PySide6.QtCore import QObject, QCoreApplication, QEvent, QPoint
from PySide6.QtGui import QCursor, QMouseEvent
from core.logger import logger


class InputSimulator(QObject):
    def __init__(self):
        super().__init__()

    def simulate_click(self, x: int, y: int, button: str = "left"):
        logger.info(f"[Input] Click at ({x}, {y}) button={button}")
        widget = QCoreApplication.instance().topLevelAt(QPoint(x, y))
        if widget:
            local = widget.mapFromGlobal(QPoint(x, y))
            btn = {
                "left": Qt.MouseButton.LeftButton,
                "right": Qt.MouseButton.RightButton,
                "middle": Qt.MouseButton.MiddleButton,
            }.get(button, Qt.MouseButton.LeftButton)
            press = QMouseEvent(QEvent.Type.MousePress, local, QPoint(x, y), btn, btn, Qt.KeyboardModifier.NoModifier)
            release = QMouseEvent(QEvent.Type.MouseRelease, local, QPoint(x, y), btn, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
            QCoreApplication.sendEvent(widget, press)
            QCoreApplication.sendEvent(widget, release)
            return True
        logger.warning(f"[Input] No widget at ({x}, {y})")
        return False

    def simulate_move(self, x: int, y: int):
        logger.info(f"[Input] Move to ({x}, {y})")
        QCursor.setPos(x, y)
        return True

    def simulate_key(self, key_text: str):
        logger.info(f"[Input] Key: {key_text}")
        return True


input_simulator = InputSimulator()
