"""ExecutionController — centralized execution state machine.

Extracted from MainWindow to eliminate scattered state mutations,
duplicated event emissions, and the QTimer loop-restart hack.

Owns:
- _loop_mode flag (single source of truth)
- _running flag (engine busy)
- QTimer loop restart logic
- Bridge to system_events.loop_mode_changed (single emission point)
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from core.logger import logger


class ExecutionController(QObject):
    """Manages execution lifecycle: idle → single-run → loop → stop.

    Public API:
        execute_once()    — single run, disables loop mode
        toggle_loop()     — start looping or stop
        stop()            — stop execution + disable loop mode
        execute()         — raw execute, does NOT touch loop mode (Bridge "run")
        enable_loop()     — enable loop mode only (Bridge "loop_on")
        disable_loop()    — disable loop mode only (Bridge "loop_off")

    Signals:
        state_changed()   — MainWindow connects to sync toolbar/menu UI
    """

    state_changed = Signal()

    def __init__(
        self,
        engine,                     # ui.qt_engine.QtExecutionEngine
        graph_getter: Callable,     # () -> NodeGraphQt.NodeGraph
        on_before_execute: Callable | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._engine = engine
        self._get_graph = graph_getter
        self._on_before_execute = on_before_execute

        self._loop_mode = False
        self._running = False
        self._streaming_mode = False

        # Listen to engine lifecycle for state tracking + loop restart
        engine.execution_started.connect(self._on_started)
        engine.execution_finished.connect(self._on_finished)

    # ------------------------------------------------------------------
    # Read-only state queries
    # ------------------------------------------------------------------

    @property
    def loop_mode(self) -> bool:
        """Whether loop mode is active (read-only from outside)."""
        return self._loop_mode

    @property
    def is_running(self) -> bool:
        """Whether the engine is currently executing."""
        return self._running

    @property
    def streaming_mode(self) -> bool:
        """Whether streaming mode is active."""
        return self._streaming_mode

    def set_streaming_mode(self, enabled: bool):
        """Switch between batch and streaming execution."""
        self._streaming_mode = enabled
        self._engine.set_streaming_mode(enabled)
        self.state_changed.emit()
        logger.info(f"Streaming mode: {'enabled' if enabled else 'disabled'}")

    # ------------------------------------------------------------------
    # Public API — toolbar / menu / bridge
    # ------------------------------------------------------------------

    def execute_once(self):
        """Single execution. Disables loop mode first, then runs."""
        self._set_loop_mode(False)
        self._execute()

    def toggle_loop(self):
        """Toggle loop: if looping → stop; if idle → start looping."""
        if self._loop_mode:
            self.stop()
        else:
            self._set_loop_mode(True)
            if not self._running:
                self._execute()

    def stop(self):
        """Stop execution and disable loop mode.

        Idempotent: safe to call when already stopped.
        """
        self._set_loop_mode(False)
        if self._running:
            self._engine.cancel()
            logger.info("Execution stop requested")

    def execute(self):
        """Raw execute — does NOT change loop mode.

        Used by BridgeCommandHandler "run" action, and by the
        internal loop-restart QTimer.
        """
        self._execute()

    def enable_loop(self):
        """Enable loop mode without starting execution.

        Used by BridgeCommandHandler "loop_on" action.
        The bridge calls execute() separately after this.
        """
        self._set_loop_mode(True)

    def disable_loop(self):
        """Disable loop mode without cancelling execution.

        Used by BridgeCommandHandler "loop_off" action.
        If currently running, the run completes but won't restart.
        """
        self._set_loop_mode(False)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _set_loop_mode(self, enabled: bool):
        """Single source of truth for _loop_mode changes.

        Every mutation goes through here — guarantees UI sync
        and event emission happen exactly once.
        """
        if self._loop_mode == enabled:
            return
        self._loop_mode = enabled
        self.state_changed.emit()

        from core.events import system_events
        system_events.loop_mode_changed.emit(enabled)

        if enabled:
            logger.info("Loop mode enabled")
        else:
            logger.info("Loop mode disabled")

    def _execute(self):
        """Trigger engine execution. Resets node states first."""
        if self._on_before_execute:
            self._on_before_execute()
        graph = self._get_graph()
        self._engine.execute(graph)

    def _on_started(self):
        """Engine callback: mark running, notify UI."""
        self._running = True
        self.state_changed.emit()

    def _on_finished(self, _result):
        """Engine callback: mark idle, restart if looping.

        Uses QTimer.singleShot(5ms) to let the previous QThread
        finish its quit() cycle before starting a new one.
        Without this delay, QThread.isRunning() would still
        return True and _engine.execute() would silently skip.
        """
        self._running = False
        self.state_changed.emit()

        if self._loop_mode:
            QTimer.singleShot(5, self._execute)
