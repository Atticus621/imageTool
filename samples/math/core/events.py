"""Pure Python EventEmitter — zero Qt dependency.

Replaces PySide6.QtCore.Signal for all core and systems code.
UI adapters bridge these to Qt Signals when needed.
"""

from __future__ import annotations

from typing import Any, Callable

from core.logger import logger


class EventEmitter:
    """Pure Python typed event.

    Usage:
        on_data = EventEmitter("on_data")
        on_data.connect(lambda x: print(x))
        on_data.emit("hello")

    Args:
        name: Optional name for tracing. If not provided, uses a default.
    """

    def __init__(self, name: str = ""):
        self._listeners: list[Callable[..., None]] = []
        self._name = name or f"EventEmitter@{id(self):#x}"

    def connect(self, callback: Callable[..., None]) -> None:
        """Register a listener. Does nothing if already registered."""
        if callback not in self._listeners:
            self._listeners.append(callback)
            cb_name = getattr(callback, "__qualname__", str(callback))
            logger.debug(f"[EventTrace] {self._name} ← {cb_name}")

    def disconnect(self, callback: Callable[..., None]) -> None:
        """Remove a previously registered listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def emit(self, *args: Any) -> None:
        """Notify all listeners. Iterates over a copy so handlers
        can safely disconnect themselves during emission."""
        args_str = ", ".join(str(a)[:50] for a in args)
        logger.debug(f"[EventTrace] → {self._name}({args_str})")
        for cb in self._listeners[:]:
            try:
                cb(*args)
            except Exception:
                cb_name = getattr(cb, "__qualname__", str(cb))
                logger.exception(
                    f"[EventTrace] Error in {self._name} listener {cb_name}"
                )

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()

    @property
    def listener_count(self) -> int:
        """Number of registered listeners (useful for testing)."""
        return len(self._listeners)


# ------------------------------------------------------------------
# 应用级事件总线
#
# UI 层与系统层通过此总线解耦通信，避免 UI 直接 import 节点实现模块。
# ------------------------------------------------------------------

class SystemEventBus:
    """应用级事件总线。

    UI 发出事件，系统层/节点层订阅。消除跨层直接 import。
    """
    loop_mode_changed = EventEmitter()  # (enabled: bool)


system_events = SystemEventBus()
