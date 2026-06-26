"""QtExecutionAdapter — QThread wrapper for pure Python ExecutionEngine.

Allows using the pure-Python systems.execution.engine.ExecutionEngine
with Qt's signal/slot system for thread-safe UI updates.

Usage:
    from systems.execution.engine import ExecutionEngine

    engine = ExecutionEngine()
    adapter = QtExecutionAdapter(engine, parent=main_window)

    # Connect to Qt Signals as usual:
    adapter.execution_started.connect(self._on_started)
    adapter.execution_finished.connect(self._on_finished)

    # Execute:
    adapter.execute(graph)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

if TYPE_CHECKING:
    from NodeGraphQt import NodeGraph
    from systems.execution.engine import ExecutionEngine


class QtExecutionAdapter(QObject):
    """Wraps a pure Python ExecutionEngine for safe Qt integration.

    Creates a QThread for execution, bridges EventEmitter callbacks
    to Qt Signals on the main thread.
    """

    execution_started = Signal()
    execution_finished = Signal(object)  # ExecutionResult
    node_state_changed = Signal(str, str)
    progress_updated = Signal(int, int)

    def __init__(self, engine: "ExecutionEngine", parent: QObject | None = None):
        super().__init__(parent)
        self._engine = engine
        self._thread: QThread | None = None

        # Bridge pure events → Qt Signals (safe cross-thread)
        engine.on_started.connect(self._emit_started)
        engine.on_finished.connect(self._emit_finished)
        engine.on_node_state_changed.connect(self._emit_node_state)
        engine.on_progress.connect(self._emit_progress)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, graph: "NodeGraph"):
        if self._thread and self._thread.isRunning():
            return

        def _run():
            self._engine.execute(graph)

        self._thread = QThread()
        self._thread.started.connect(_run)
        self._thread.start()

    def cancel(self):
        self._engine.cancel()

    # ------------------------------------------------------------------
    # Event → Qt Signal bridges (invoke via QMetaObject for thread safety)
    # ------------------------------------------------------------------

    def _emit_started(self):
        self.execution_started.emit()

    def _emit_finished(self, result):
        self.execution_finished.emit(result)

    def _emit_node_state(self, name: str, state: str):
        self.node_state_changed.emit(name, state)

    def _emit_progress(self, current: int, total: int):
        self.progress_updated.emit(current, total)
