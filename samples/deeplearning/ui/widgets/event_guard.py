"""EventGuard — 管理 QWidget 的鼠标事件拦截状态。

状态机：
    IDLE → 按下左键 → DRAWING → 释放左键 → CONSUMED → 鼠标离开 → IDLE

DRAWING 期间：所有事件被拦截（正在绘制）
CONSUMED 期间：所有事件被拦截（防止穿透到 viewport）
IDLE 期间：事件正常传播

使用方式：
    guard = EventGuard()

    def mousePressEvent(self, event):
        if guard.on_press(event):
            # 处理绘制开始
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if guard.on_move(event):
            if guard.is_drawing:
                # 处理绘制中
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if guard.on_release(event):
            # 处理绘制结束
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        guard.on_leave()
        super().leaveEvent(event)
"""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import Qt
from PySide6.QtGui import QInputEvent

from core.logger import logger


class EventGuard:
    """管理鼠标事件拦截状态。"""

    class State(Enum):
        IDLE = auto()
        DRAWING = auto()
        CONSUMED = auto()

    def __init__(self):
        self._state = self.State.IDLE

    def on_press(self, event: QInputEvent) -> bool:
        """处理鼠标按下事件。左键按下时进入 DRAWING 状态。

        Returns:
            True 表示事件被拦截，调用方应处理并 return。
            False 表示事件未拦截，调用方应调用 super()。
        """
        if event.button() == Qt.MouseButton.LeftButton:
            old = self._state.name
            self._state = self.State.DRAWING
            logger.debug(f"[EventGuard] {old} → DRAWING")
            event.accept()
            return True
        return False

    def on_move(self, event: QInputEvent) -> bool:
        """处理鼠标移动事件。DRAWING 或 CONSUMED 状态时拦截。

        Returns:
            True 表示事件被拦截。
            False 表示事件未拦截。
        """
        if self._state in (self.State.DRAWING, self.State.CONSUMED):
            event.accept()
            return True
        return False

    def on_release(self, event: QInputEvent) -> bool:
        """处理鼠标释放事件。DRAWING 状态释放左键时进入 CONSUMED 状态。

        Returns:
            True 表示事件被拦截。
            False 表示事件未拦截。
        """
        if event.button() == Qt.MouseButton.LeftButton and self._state == self.State.DRAWING:
            old = self._state.name
            self._state = self.State.CONSUMED
            logger.debug(f"[EventGuard] {old} → CONSUMED")
            event.accept()
            return True
        if self._state == self.State.CONSUMED:
            event.accept()
            return True
        return False

    def on_leave(self) -> None:
        """鼠标离开时重置为 IDLE 状态。"""
        if self._state != self.State.IDLE:
            logger.debug(f"[EventGuard] {self._state.name} → IDLE (leaveEvent)")
        self._state = self.State.IDLE

    @property
    def is_drawing(self) -> bool:
        """是否正在绘制中。"""
        return self._state == self.State.DRAWING
