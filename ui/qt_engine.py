"""Qt execution engine wrapper.

Wraps the pure Python ExecutionEngine with Qt Signals for UI compatibility.
Handles QThread management and EventEmitter → Qt Signal bridging.
"""

from PySide6.QtCore import QObject, QThread, Signal

from core.logger import logger
from core.node_base.registry import node_registry
from core.node_base.node import NodeState
from systems.execution.engine import ExecutionEngine as PureEngine
from systems.execution.topology import topological_sort
from systems.execution.worker import ExecutionWorker as PureWorker
from systems.execution.result import ExecutionResult


class QtExecutionWorker(QObject):
    """Qt wrapper for pure Python ExecutionWorker.

    Bridges EventEmitter → Qt Signal for thread-safe UI updates.
    """

    progress = Signal(int, int)
    node_started = Signal(str)
    node_finished = Signal(str, bool)
    image_output = Signal(object)
    all_finished = Signal(object)

    def __init__(self, sorted_nodes: list, node_infos: dict):
        super().__init__()
        self._pure = PureWorker(sorted_nodes, node_infos)

    def cancel(self):
        self._pure.cancel()

    def run(self):
        """Run worker, bridging EventEmitter → Qt Signal."""
        self._pure.on_progress.connect(lambda c, t: self.progress.emit(c, t))
        self._pure.on_node_started.connect(lambda n: self.node_started.emit(n))
        self._pure.on_node_finished.connect(lambda n, s: self.node_finished.emit(n, s))
        self._pure.on_image_output.connect(lambda e: self.image_output.emit(e))
        self._pure.on_all_finished.connect(lambda r: self.all_finished.emit(r))
        self._pure.run()


class QtExecutionEngine(QObject):
    """Qt wrapper for pure Python ExecutionEngine.

    Provides Qt Signals for UI integration and manages QThread for
    background execution.
    """

    execution_started = Signal()
    execution_finished = Signal(object)
    node_state_changed = Signal(str, str)
    progress_updated = Signal(int, int)
    image_output = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: QtExecutionWorker | None = None

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

            info = gn.to_pipeline_info()
            node_infos[gn] = info

            exec_node = node_registry.create_node(node_id)
            if exec_node:
                exec_nodes[gn] = exec_node
                exec_node.set_state(NodeState.RUNNING)
                self.node_state_changed.emit(gn.name(), "running")
            else:
                logger.warning(f"Cannot create execution node for: {node_id}")

        self._thread = QThread()
        self._worker = QtExecutionWorker(sorted_nodes, node_infos)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress_updated)
        self._worker.node_finished.connect(self._on_worker_node_finished)
        self._worker.image_output.connect(self.image_output)
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
