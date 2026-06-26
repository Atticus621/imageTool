"""Pure Python EventEmitter — zero Qt dependency.

Replaces PySide6.QtCore.Signal for all core and systems code.
UI adapters bridge these to Qt Signals when needed.
"""

from __future__ import annotations

from typing import Any, Callable


class EventEmitter:
    """Pure Python typed event.

    Usage:
        on_data = EventEmitter()
        on_data.connect(lambda x: print(x))
        on_data.emit("hello")
    """

    def __init__(self):
        self._listeners: list[Callable[..., None]] = []

    def connect(self, callback: Callable[..., None]) -> None:
        """Register a listener. Does nothing if already registered."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def disconnect(self, callback: Callable[..., None]) -> None:
        """Remove a previously registered listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def emit(self, *args: Any) -> None:
        """Notify all listeners. Iterates over a copy so handlers
        can safely disconnect themselves during emission."""
        for cb in self._listeners[:]:
            cb(*args)

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()

    @property
    def listener_count(self) -> int:
        """Number of registered listeners (useful for testing)."""
        return len(self._listeners)
