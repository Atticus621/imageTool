"""ExecutionWorker — pure Python pipeline runner.

Zero Qt dependency. Uses core.events.EventEmitter for progress/state
notifications and threading.Thread for background execution.
"""

from __future__ import annotations

import threading

from core.events import EventEmitter
from core.logger import logger
from core.node_base.node import NodeBase, NodeState
from core.pipeline import PipelineNodeInfo
from systems.execution.result import ExecutionResult, ImageSetEntry


class ExecutionWorker:
    """Processes graph nodes in topological order on a background thread.

    Events (via EventEmitter):
        on_progress:     (current: int, total: int)
        on_node_started: (name: str)
        on_node_finished:(name: str, success: bool)
        on_all_finished: (result: ExecutionResult)
    """

    def __init__(self, sorted_nodes: list, exec_nodes: dict, node_infos: dict):
        self._sorted_nodes = sorted_nodes
        self._exec_nodes = exec_nodes
        self._node_infos = node_infos
        self._cancelled = False
        self._cancel_lock = threading.Lock()

        # EventEmitters (replaces Qt Signals)
        self.on_progress = EventEmitter()
        self.on_node_started = EventEmitter()
        self.on_node_finished = EventEmitter()
        self.on_all_finished = EventEmitter()

    def cancel(self):
        with self._cancel_lock:
            self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        with self._cancel_lock:
            return self._cancelled

    def run(self):
        """Execute all nodes in topological order. Called from a worker thread."""
        total = len(self._sorted_nodes)
        all_success = True

        for i, graph_node in enumerate(self._sorted_nodes):
            if self.is_cancelled:
                logger.info("Execution cancelled")
                self.on_all_finished.emit(ExecutionResult(success=False))
                return

            info = self._node_infos.get(graph_node)
            exec_node = self._exec_nodes.get(graph_node)

            if exec_node is None or info is None:
                logger.warning(f"No execution node for: {graph_node.name()}")
                self.on_node_finished.emit(graph_node.name(), False)
                all_success = False
                continue

            self.on_node_started.emit(info.name)
            self.on_progress.emit(i + 1, total)

            logger.info(f"Executing node: {info.name} ({info.node_id})")

            try:
                exec_node.params.update(info.param_values)
                logger.info(f"  Params: {exec_node.params}")

                self._feed_input_data(graph_node, exec_node, info)

                success = exec_node.execute()

                self.on_node_finished.emit(info.name, success)
                if not success:
                    all_success = False

            except Exception as e:
                logger.error(f"Node {info.name} failed: {e}")
                import traceback
                traceback.print_exc()
                exec_node.set_state(NodeState.ERROR)
                self.on_node_finished.emit(info.name, False)
                all_success = False

        result = self._collect_image_sets(all_success)
        self.on_all_finished.emit(result)

    def _feed_input_data(self, graph_node, exec_node: NodeBase, info: PipelineNodeInfo):
        for port in graph_node.input_ports():
            graph_port_name = port.name()
            exec_port_name = info.port_label_to_name.get(graph_port_name, graph_port_name)
            target_port = exec_node.get_input_port(exec_port_name)
            if target_port is None:
                logger.warning(f"  Input port not found: {exec_port_name}")
                continue

            connected = port.connected_ports()
            if connected:
                all_images = []
                for src_port in connected:
                    src_node = src_port.node()
                    src_exec = self._exec_nodes.get(src_node)
                    if src_exec:
                        src_info = self._node_infos.get(src_node)
                        src_port_name = src_port.name()
                        src_exec_port_name = (
                            src_info.port_label_to_name.get(src_port_name, src_port_name)
                            if src_info else src_port_name
                        )
                        src_output = src_exec.get_output_port(src_exec_port_name)
                        if src_output and src_output.data is not None:
                            data = src_output.data
                            images = data if isinstance(data, list) else [data]
                            all_images.extend(images)
                            logger.info(
                                f"  Got {len(images)} images from "
                                f"{src_node.name()}:{src_exec_port_name}"
                            )

                if all_images:
                    target_port.data = all_images
                    logger.info(
                        f"  Fed total {len(all_images)} images -> {exec_port_name}"
                    )

    def _collect_image_sets(self, success: bool) -> ExecutionResult:
        input_sets = []
        output_sets = []

        for graph_node, exec_node in self._exec_nodes.items():
            info = self._node_infos.get(graph_node)
            if info is None:
                continue

            has_downstream = any(
                p.connected_ports() for p in graph_node.output_ports()
            )
            has_upstream = any(
                p.connected_ports() for p in graph_node.input_ports()
            )

            for port in graph_node.output_ports():
                exec_port_name = info.port_label_to_name.get(port.name(), port.name())
                exec_port = exec_node.get_output_port(exec_port_name)
                if exec_port and exec_port.data is not None:
                    data = exec_port.data
                    images = data if isinstance(data, list) else [data]
                    if images:
                        entry = ImageSetEntry(
                            name=f"{info.name}:{port.name()}",
                            images=images,
                        )
                        if not has_upstream:
                            input_sets.append(entry)
                        if not has_downstream:
                            output_sets.append(entry)

        logger.info(
            f"Collected {len(input_sets)} input sets, "
            f"{len(output_sets)} output sets"
        )
        return ExecutionResult(
            success=success, input_sets=input_sets, output_sets=output_sets
        )
