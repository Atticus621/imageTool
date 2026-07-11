"""Backward-compatibility shim.

For now, keeps the QObject-based ExecutionEngine so existing Qt
signal connections in MainWindow continue to work. New code can
use systems.execution.engine (pure Python) with the Qt adapter
in ui/adapters/qt_execution_adapter.py when ready.
"""

from systems.execution.engine import ExecutionEngine as _PureEngine
from systems.execution.topology import topological_sort  # noqa: F401
from systems.execution.worker import ExecutionWorker as _PureWorker

from PySide6.QtCore import QObject, QThread, Signal
from core.logger import logger
from core.node_base.registry import node_registry
from core.node_base.node import NodeState
from core.pipeline import PipelineNodeInfo
from systems.execution.result import ExecutionResult


class ExecutionWorker(QObject):
    """Qt-based worker (backward-compat wrapper).

    Bridges the pure Python ExecutionWorker's EventEmitters to Qt Signals
    for thread-safe UI updates.
    """

    progress = Signal(int, int)
    node_started = Signal(str)
    node_finished = Signal(str, bool)
    all_finished = Signal(object)

    def __init__(self, sorted_nodes: list, node_infos: dict):
        super().__init__()
        self._pure = _PureWorker(sorted_nodes, node_infos)

    def cancel(self):
        self._pure.cancel()

    def run(self):
        """Wraps pure worker.run(), bridging EventEmitter → Qt Signal."""
        self._pure.on_progress.connect(lambda c, t: self.progress.emit(c, t))
        self._pure.on_node_started.connect(lambda n: self.node_started.emit(n))
        self._pure.on_node_finished.connect(lambda n, s: self.node_finished.emit(n, s))
        self._pure.on_all_finished.connect(lambda r: self.all_finished.emit(r))
        self._pure.run()


class ExecutionEngine(QObject):
    """Qt-based engine (backward-compat wrapper).

    Wraps the pure Python ExecutionEngine, bridging its EventEmitters
    to Qt Signals for MainWindow compatibility.
    """

    execution_started = Signal()
    execution_finished = Signal(object)
    node_state_changed = Signal(str, str)
    progress_updated = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pure = _PureEngine()
        self._thread: QThread | None = None
        self._worker: ExecutionWorker | None = None

        # Wire pure engine events → Qt Signals
        self._pure.on_started.connect(lambda: self.execution_started.emit())
        self._pure.on_finished.connect(lambda r: self.execution_finished.emit(r))
        self._pure.on_node_state_changed.connect(
            lambda n, s: self.node_state_changed.emit(n, s)
        )
        self._pure.on_progress.connect(
            lambda c, t: self.progress_updated.emit(c, t)
        )

    def execute(self, graph):
        if self._thread and self._thread.isRunning():
            logger.warning("Execution already in progress")
            return

        graph_nodes = graph.all_nodes()
        if not graph_nodes:
            logger.warning("No nodes to execute")
            self.execution_finished.emit(ExecutionResult(success=True))
            return

        sorted_nodes = topological_sort(graph_nodes)
        logger.info(f"Execution order: {[n.name() for n in sorted_nodes]}")

        node_infos = {}
        exec_nodes = {}
        for gn in sorted_nodes:
            node_id = getattr(gn, "_node_id", "")
            if not node_id:
                logger.warning(f"Node {gn.name()} has no type, skipping")
                continue

            info = PipelineNodeInfo(
                node_id=node_id,
                name=gn.name(),
                param_values=dict(getattr(gn, "_param_values", {})),
                port_label_to_name=dict(getattr(gn, "_port_label_to_name", {})),
            )
            node_infos[gn] = info

            exec_node = node_registry.create_node(node_id)
            if exec_node:
                exec_nodes[gn] = exec_node
                exec_node.set_state(NodeState.RUNNING)
                self.node_state_changed.emit(gn.name(), "running")
            else:
                logger.warning(f"Cannot create execution node for: {node_id}")

        self._thread = QThread()
        self._worker = ExecutionWorker(sorted_nodes, node_infos)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress_updated)
        self._worker.node_finished.connect(self._on_worker_node_finished)
        self._worker.all_finished.connect(self._on_worker_all_finished)
        self._worker.all_finished.connect(self._thread.quit)

        self.execution_started.emit()
        self._thread.start()

    def cancel(self):
        if self._worker:
            self._worker.cancel()

    def _on_worker_node_finished(self, name: str, success: bool):
        state = "success" if success else "error"
        self.node_state_changed.emit(name, state)

    def _on_worker_all_finished(self, result: ExecutionResult):
        self.execution_finished.emit(result)
