"""ExecutionEngine — pure Python pipeline execution coordinator.

Zero Qt dependency. Uses threading.Thread + EventEmitter instead of
QThread + QSignal. UI bridges to Qt via ui/adapters/qt_execution_adapter.py.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from core.events import EventEmitter
from core.interfaces import IExecutionProvider
from core.logger import logger
from core.node_base.registry import node_registry
from core.node_base.node import NodeState
from core.pipeline import PipelineNodeInfo
from systems.execution.result import ExecutionResult
from systems.execution.topology import topological_sort
from systems.execution.worker import ExecutionWorker

if TYPE_CHECKING:
    from NodeGraphQt import NodeGraph


class ExecutionEngine(IExecutionProvider):
    """Coordinates pipeline execution on a background thread.

    Events (all via EventEmitter):
        on_started:           ()
        on_finished:          (ExecutionResult)
        on_node_state_changed:(name: str, state: str)
        on_progress:          (current: int, total: int)
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._worker: ExecutionWorker | None = None

        # EventEmitters (replaces Qt Signals)
        self.on_started = EventEmitter()
        self.on_finished = EventEmitter()
        self.on_node_state_changed = EventEmitter()
        self.on_progress = EventEmitter()

    def execute(self, graph: "NodeGraph"):
        if self._thread and self._thread.is_alive():
            logger.warning("Execution already in progress")
            return

        graph_nodes = graph.all_nodes()
        if not graph_nodes:
            logger.warning("No nodes to execute")
            self.on_finished.emit(ExecutionResult(success=True))
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

            # Use GraphNode.to_pipeline_info() as single source of truth
            info = gn.to_pipeline_info()
            node_infos[gn] = info
            logger.info(f"[Engine] Node '{gn.name()}': {info}")

            exec_node = node_registry.create_node(node_id)
            if exec_node:
                exec_nodes[gn] = exec_node
                exec_node.set_state(NodeState.RUNNING)
                self.on_node_state_changed.emit(gn.name(), "running")
            else:
                logger.warning(f"Cannot create execution node for: {node_id}")

        self._worker = ExecutionWorker(sorted_nodes, exec_nodes, node_infos)

        # Wire worker events → engine events
        self._worker.on_progress.connect(
            lambda c, t: self.on_progress.emit(c, t)
        )
        self._worker.on_node_started.connect(
            lambda n: self._on_node_started(n)
        )
        self._worker.on_node_finished.connect(
            lambda n, s: self._on_node_finished(n, s)
        )
        self._worker.on_all_finished.connect(
            lambda r: self._on_all_finished(r)
        )

        self._thread = threading.Thread(target=self._worker.run, daemon=True)
        self.on_started.emit()
        self._thread.start()

    def cancel(self):
        """Cancel the current execution (thread-safe)."""
        if self._worker:
            self._worker.cancel()

    # ------------------------------------------------------------------
    # Internal event handlers
    # ------------------------------------------------------------------

    def _on_node_started(self, name: str):
        logger.info(f"Node started: {name}")
        self.on_node_state_changed.emit(name, "running")

    def _on_node_finished(self, name: str, success: bool):
        state = "success" if success else "error"
        logger.info(f"Node finished: {name} -> {state}")
        self.on_node_state_changed.emit(name, state)

    def _on_all_finished(self, result: ExecutionResult):
        logger.info(
            f"Execution finished: {'success' if result.success else 'failed'}"
        )
        self.on_finished.emit(result)
