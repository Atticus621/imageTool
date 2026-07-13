"""Error bus — pure Python event system for error reporting.

Zero Qt dependency. Uses core.events.EventEmitter instead of QSignal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.events import EventEmitter
from core.logger import logger


@dataclass
class ErrorEntry:
    code: str
    message: str
    details: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class ErrorBus:
    """Central error reporting bus.

    Systems and UI can connect to error_occurred to react to errors.
    Maintains a bounded history of recent errors.
    """

    def __init__(self):
        self.error_occurred = EventEmitter()
        self._history: list[ErrorEntry] = []
        self._max_history = 100

    def report(self, code: str, message: str, details: dict = None):
        entry = ErrorEntry(code=code, message=message, details=details or {})
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        logger.error(f"[{code}] {message} {details or {}}")
        self.error_occurred.emit(code, message, entry.details)

    def get_recent(self, count: int = 10) -> list[dict]:
        return [e.to_dict() for e in self._history[-count:]]

    def clear(self):
        self._history.clear()


error_bus = ErrorBus()
