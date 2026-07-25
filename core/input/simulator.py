"""InputSimulator — 通过注入 Qt GUI 事件模拟用户交互。

所有事件通过 QCoreApplication.sendEvent() 或 QApplication.postEvent()
直接注入到目标 widget，走正常的 Qt 事件处理流程，不调用任何中间层 API。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QObject, QCoreApplication, QEvent, QPoint, QPointF, QTimer, Qt,
)
from PySide6.QtGui import QCursor, QMouseEvent, QKeyEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QWidget

from core.logger import logger

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Key name → Qt.Key 映射
# ---------------------------------------------------------------------------

_KEY_MAP: dict[str, int] = {
    "delete": Qt.Key.Key_Delete,
    "backspace": Qt.Key.Key_Backspace,
    "escape": Qt.Key.Key_Escape,
    "esc": Qt.Key.Key_Escape,
    "return": Qt.Key.Key_Return,
    "enter": Qt.Key.Key_Return,
    "tab": Qt.Key.Key_Tab,
    "space": Qt.Key.Key_Space,
    "up": Qt.Key.Key_Up,
    "down": Qt.Key.Key_Down,
    "left": Qt.Key.Key_Left,
    "right": Qt.Key.Key_Right,
    "home": Qt.Key.Key_Home,
    "end": Qt.Key.Key_End,
    "pageup": Qt.Key.Key_PageUp,
    "pagedown": Qt.Key.Key_PageDown,
    "f1": Qt.Key.Key_F1,
    "f2": Qt.Key.Key_F2,
    "f3": Qt.Key.Key_F3,
    "f4": Qt.Key.Key_F4,
    "f5": Qt.Key.Key_F5,
    "f6": Qt.Key.Key_F6,
    "f7": Qt.Key.Key_F7,
    "f8": Qt.Key.Key_F8,
    "f9": Qt.Key.Key_F9,
    "f10": Qt.Key.Key_F10,
    "f11": Qt.Key.Key_F11,
    "f12": Qt.Key.Key_F12,
    "ctrl": Qt.Key.Key_Control,
    "shift": Qt.Key.Key_Shift,
    "alt": Qt.Key.Key_Alt,
    "a": Qt.Key.Key_A,
    "c": Qt.Key.Key_C,
    "v": Qt.Key.Key_V,
    "x": Qt.Key.Key_X,
    "z": Qt.Key.Key_Z,
    "y": Qt.Key.Key_Y,
    "s": Qt.Key.Key_S,
    "o": Qt.Key.Key_O,
    "n": Qt.Key.Key_N,
}

_MODIFIER_MAP: dict[str, int] = {
    "ctrl": Qt.KeyboardModifier.ControlModifier,
    "shift": Qt.KeyboardModifier.ShiftModifier,
    "alt": Qt.KeyboardModifier.AltModifier,
    "meta": Qt.KeyboardModifier.MetaModifier,
}

_BTN_MAP: dict[str, Qt.MouseButton] = {
    "left": Qt.MouseButton.LeftButton,
    "right": Qt.MouseButton.RightButton,
    "middle": Qt.MouseButton.MiddleButton,
}


def _resolve_key(name: str) -> int:
    """将按键名转为 Qt.Key 值。"""
    low = name.lower().strip()
    if low in _KEY_MAP:
        return _KEY_MAP[low]
    if len(low) == 1:
        return ord(low.upper())
    raise ValueError(f"Unknown key: {name}")


def _parse_modifiers(mod_str: str) -> Qt.KeyboardModifier:
    """解析修饰键字符串，如 'ctrl+shift' → ControlModifier|ShiftModifier。"""
    mods = Qt.KeyboardModifier.NoModifier
    for part in mod_str.lower().split("+"):
        part = part.strip()
        if part in _MODIFIER_MAP:
            mods |= _MODIFIER_MAP[part]
    return mods


def _btn_enum(button: str) -> Qt.MouseButton:
    return _BTN_MAP.get(button.lower(), Qt.MouseButton.LeftButton)


def _btns_from_btn(btn: Qt.MouseButton) -> Qt.MouseButton:
    """press 事件的 buttons 字段需包含当前按下的按钮。"""
    return btn


class InputSimulator(QObject):
    """通过 Qt 事件注入模拟用户输入。

    所有 simulate_* 方法接收一个 widget 参数（目标 widget），
    和事件的局部坐标（相对于 widget 或其 viewport）。
    """

    # ------------------------------------------------------------------
    # Mouse click
    # ------------------------------------------------------------------

    def simulate_click(
        self,
        widget: QWidget,
        x: int,
        y: int,
        button: str = "left",
    ) -> bool:
        """在 widget 的局部坐标 (x, y) 处模拟一次完整点击（press + release）。"""
        logger.info(f"[Sim] Click ({x}, {y}) btn={button} on {widget.__class__.__name__}")
        target = self._event_target(widget)
        local = QPointF(x, y)
        global_pt = target.mapToGlobal(QPoint(x, y))
        btn = _btn_enum(button)

        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            local, global_pt, btn, _btns_from_btn(btn),
            Qt.KeyboardModifier.NoModifier,
        )
        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            local, global_pt, btn, Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )

        QApplication.sendEvent(target, press)
        QApplication.sendEvent(target, release)
        return True

    # ------------------------------------------------------------------
    # Mouse double-click
    # ------------------------------------------------------------------

    def simulate_double_click(
        self,
        widget: QWidget,
        x: int,
        y: int,
        button: str = "left",
    ) -> bool:
        """模拟双击（press → release → dblclick → release）。"""
        logger.info(f"[Sim] DblClick ({x}, {y}) btn={button} on {widget.__class__.__name__}")
        target = self._event_target(widget)
        local = QPointF(x, y)
        global_pt = target.mapToGlobal(QPoint(x, y))
        btn = _btn_enum(button)
        no_btn = Qt.MouseButton.NoButton
        no_mod = Qt.KeyboardModifier.NoModifier

        events = [
            QMouseEvent(QEvent.Type.MouseButtonPress, local, global_pt, btn, btn, no_mod),
            QMouseEvent(QEvent.Type.MouseButtonRelease, local, global_pt, btn, no_btn, no_mod),
            QMouseEvent(QEvent.Type.MouseButtonDblClick, local, global_pt, btn, btn, no_mod),
            QMouseEvent(QEvent.Type.MouseButtonRelease, local, global_pt, btn, no_btn, no_mod),
        ]
        for evt in events:
            QApplication.sendEvent(target, evt)
        return True

    # ------------------------------------------------------------------
    # Mouse right-click
    # ------------------------------------------------------------------

    def simulate_right_click(self, widget: QWidget, x: int, y: int) -> bool:
        """模拟右键点击。"""
        return self.simulate_click(widget, x, y, button="right")

    # ------------------------------------------------------------------
    # Mouse move
    # ------------------------------------------------------------------

    def simulate_move(self, widget: QWidget, x: int, y: int) -> bool:
        """模拟鼠标移动到 widget 局部坐标 (x, y)。"""
        logger.info(f"[Sim] Move ({x}, {y}) on {widget.__class__.__name__}")
        target = self._event_target(widget)
        local = QPointF(x, y)
        global_pt = target.mapToGlobal(QPoint(x, y))

        event = QMouseEvent(
            QEvent.Type.MouseMove,
            local, global_pt,
            Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(target, event)
        return True

    # ------------------------------------------------------------------
    # Mouse drag
    # ------------------------------------------------------------------

    def simulate_drag(
        self,
        widget: QWidget,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        button: str = "left",
        steps: int = 10,
        duration_ms: int = 0,
        callback: object = None,
    ) -> bool:
        """模拟从 (x1,y1) 拖拽到 (x2,y2)。

        steps: 中间 move 事件数量。
        duration_ms: 如果 > 0，move 事件通过 QTimer 分步发送（异步）；
                     否则同步发送所有事件。
        """
        logger.info(
            f"[Sim] Drag ({x1},{y1})→({x2},{y2}) btn={button} "
            f"steps={steps} dur={duration_ms}ms on {widget.__class__.__name__}"
        )
        target = self._event_target(widget)
        btn = _btn_enum(button)
        no_mod = Qt.KeyboardModifier.NoModifier

        if duration_ms > 0:
            self._async_drag(target, x1, y1, x2, y2, btn, steps, duration_ms, callback)
        else:
            self._sync_drag(target, x1, y1, x2, y2, btn, steps)
        return True

    def _sync_drag(self, target, x1, y1, x2, y2, btn, steps):
        """同步发送拖拽事件序列。"""
        no_mod = Qt.KeyboardModifier.NoModifier

        # Press
        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(x1, y1), target.mapToGlobal(QPoint(x1, y1)),
            btn, btn, no_mod,
        )
        QApplication.sendEvent(target, press)

        # Move events
        for i in range(1, steps + 1):
            t = i / steps
            mx = int(x1 + (x2 - x1) * t)
            my = int(y1 + (y2 - y1) * t)
            move = QMouseEvent(
                QEvent.Type.MouseMove,
                QPointF(mx, my), target.mapToGlobal(QPoint(mx, my)),
                Qt.MouseButton.NoButton, btn, no_mod,
            )
            QApplication.sendEvent(target, move)

        # Release
        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(x2, y2), target.mapToGlobal(QPoint(x2, y2)),
            btn, Qt.MouseButton.NoButton, no_mod,
        )
        QApplication.sendEvent(target, release)

    def _async_drag(self, target, x1, y1, x2, y2, btn, steps, duration_ms, callback):
        """通过 QTimer 分步发送拖拽事件（异步）。"""
        no_mod = Qt.KeyboardModifier.NoModifier
        interval = max(1, duration_ms // (steps + 2))

        # Press
        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(x1, y1), target.mapToGlobal(QPoint(x1, y1)),
            btn, btn, no_mod,
        )
        QApplication.sendEvent(target, press)

        # Schedule move events
        events_queue = []
        for i in range(1, steps + 1):
            t = i / steps
            mx = int(x1 + (x2 - x1) * t)
            my = int(y1 + (y2 - y1) * t)
            events_queue.append(QMouseEvent(
                QEvent.Type.MouseMove,
                QPointF(mx, my), target.mapToGlobal(QPoint(mx, my)),
                Qt.MouseButton.NoButton, btn, no_mod,
            ))

        # Release event
        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(x2, y2), target.mapToGlobal(QPoint(x2, y2)),
            btn, Qt.MouseButton.NoButton, no_mod,
        )

        def _send_next(idx):
            if idx < len(events_queue):
                QApplication.sendEvent(target, events_queue[idx])
                QTimer.singleShot(interval, lambda: _send_next(idx + 1))
            else:
                QApplication.sendEvent(target, release)
                if callback:
                    callback()

        QTimer.singleShot(interval, lambda: _send_next(0))

    # ------------------------------------------------------------------
    # Mouse wheel
    # ------------------------------------------------------------------

    def simulate_wheel(
        self,
        widget: QWidget,
        x: int,
        y: int,
        delta: int = 120,
    ) -> bool:
        """在 (x, y) 处模拟鼠标滚轮。delta > 0 向上，< 0 向下。"""
        logger.info(f"[Sim] Wheel ({x}, {y}) delta={delta} on {widget.__class__.__name__}")
        target = self._event_target(widget)
        local = QPointF(x, y)
        global_pt = target.mapToGlobal(QPoint(x, y))

        event = QWheelEvent(
            local, global_pt,
            QPoint(0, 0),
            QPoint(0, delta),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.postEvent(target, event)
        return True

    # ------------------------------------------------------------------
    # Keyboard — single key
    # ------------------------------------------------------------------

    def simulate_key_press(
        self,
        widget: QWidget,
        key: str,
        modifiers: str = "",
    ) -> bool:
        """模拟按下并释放一个按键。

        key: 按键名，如 'delete', 'escape', 'return', 'a', 'ctrl+z'。
             也可以是组合键如 'ctrl+c'（modifiers 参数会被忽略，直接从 key 解析）。
        modifiers: 修饰键，如 'ctrl', 'ctrl+shift'。如果 key 中包含 '+'，
                   则从 key 中解析修饰键。
        """
        # 如果 key 包含 '+'，从中解析修饰键
        if "+" in key:
            parts = key.lower().split("+")
            mod_parts = parts[:-1]
            actual_key = parts[-1]
            mod_str = "+".join(mod_parts)
        else:
            actual_key = key
            mod_str = modifiers

        qt_key = _resolve_key(actual_key)
        qt_mods = _parse_modifiers(mod_str) if mod_str else Qt.KeyboardModifier.NoModifier

        logger.info(
            f"[Sim] Key '{key}' (parsed: key={actual_key}, mods={mod_str}) "
            f"on {widget.__class__.__name__}"
        )

        target = self._focus_target(widget)

        press = QKeyEvent(QEvent.Type.KeyPress, qt_key, qt_mods)
        release = QKeyEvent(QEvent.Type.KeyRelease, qt_key, qt_mods)

        QApplication.sendEvent(target, press)
        QApplication.sendEvent(target, release)
        return True

    # ------------------------------------------------------------------
    # Keyboard — text input
    # ------------------------------------------------------------------

    def simulate_text(self, widget: QWidget, text: str) -> bool:
        """模拟输入一段文本（逐字符发送 Text 事件）。"""
        logger.info(f"[Sim] Text '{text}' on {widget.__class__.__name__}")
        target = self._focus_target(widget)

        for ch in text:
            event = QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_unknown,
                Qt.KeyboardModifier.NoModifier,
                ch,
            )
            QApplication.sendEvent(target, event)
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _event_target(widget: QWidget) -> QWidget:
        """解析实际的事件目标。

        如果 widget 有 viewport()（如 QGraphicsView），返回 viewport；
        否则返回 widget 本身。
        """
        if hasattr(widget, "viewport") and callable(widget.viewport):
            return widget.viewport()
        return widget

    @staticmethod
    def _focus_target(widget: QWidget) -> QWidget:
        """获取键盘事件目标。

        确保 widget 有焦点，返回实际接收键盘事件的 widget。
        """
        if not widget.hasFocus():
            widget.setFocus()
        return widget


# Singleton
input_simulator = InputSimulator()
