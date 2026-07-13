"""QtSignalBridge — generic EventEmitter → Qt Signal adapter.

Allows pure Python systems to emit events that Qt widgets can
connect to via their familiar Signal/Slot mechanism.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Signal

from core.events import EventEmitter


class QtSignalBridge(QObject):
    """Wraps an EventEmitter as a Qt Signal.

    Usage:
        bridge = QtSignalBridge(system.on_data_changed)
        bridge.signal_emitted.connect(my_qt_slot)
    """

    signal_emitted = Signal(object)

    def __init__(self, emitter: EventEmitter, parent: QObject | None = None):
        super().__init__(parent)
        emitter.connect(self._on_event)

    def _on_event(self, *args):
        # If single arg, emit it directly; wrap multiple in tuple
        if len(args) == 1:
            self.signal_emitted.emit(args[0])
        else:
            self.signal_emitted.emit(args)
