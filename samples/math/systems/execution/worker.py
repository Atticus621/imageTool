"""ExecutionWorker — pure Python pipeline runner.

Zero Qt dependency. Uses core.events.EventEmitter for progress/state
notifications and threading.Thread for background execution.

Execution is streaming: nodes are instantiated just-in-time right
before execution, and image outputs are emitted incrementally so the
viewer can display partial results without waiting for the full pipeline.
"""

from __future__ import annotations

import threading

import numpy as np

from core.events import EventEmitter
from core.image_data import ImageData
from core.math_data import MathExpression, MathMatrix
from core.logger import logger
from core.node_base.node import NodeBase, NodeState
from core.node_base.registry import node_registry
from core.pipeline import PipelineNodeInfo
from systems.execution.result import ExecutionResult, ImageSetEntry


class ExecutionWorker:
    """Processes graph nodes in topological order on a background thread.

    Execution nodes are created lazily (just-in-time) so the thread
    starts immediately without waiting for all node instances to be
    constructed.  Image outputs are emitted incrementally after each
    node completes so the viewer can show partial results.

    Events (via EventEmitter):
        on_progress:      (current: int, total: int)
        on_node_started:  (name: str)
        on_node_finished: (name: str, success: bool)
        on_image_output:  (entries: list[ImageSetEntry])
        on_all_finished:  (result: ExecutionResult)
    """

    def __init__(self, sorted_nodes: list, node_infos: dict):
        self._sorted_nodes = sorted_nodes
        self._node_infos = node_infos
        self._exec_nodes: dict = {}   # populated lazily in run()
        self._cancelled = False
        self._cancel_lock = threading.Lock()

        # EventEmitters (replaces Qt Signals)
        self.on_progress = EventEmitter()
        self.on_node_started = EventEmitter()
        self.on_node_finished = EventEmitter()
        self.on_image_output = EventEmitter()
        self.on_all_finished = EventEmitter()

    def cancel(self):
        with self._cancel_lock:
            self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        with self._cancel_lock:
            return self._cancelled

    def run(self):
        """Execute all nodes in topological order. Called from a worker thread.

        Execution nodes are created just-in-time (lazily) right before
        they execute.  Image outputs are emitted incrementally after each
        node completes, so partial results are available immediately.
        """
        total = len(self._sorted_nodes)
        all_success = True
        accumulated_entries: list[ImageSetEntry] = []

        for i, graph_node in enumerate(self._sorted_nodes):
            if self.is_cancelled:
                logger.info("Execution cancelled")
                self.on_all_finished.emit(ExecutionResult(success=False))
                return

            info = self._node_infos.get(graph_node)
            if info is None:
                logger.warning(f"No pipeline info for: {graph_node.name()}")
                self.on_node_finished.emit(graph_node.name(), False)
                all_success = False
                continue

            # --- Lazy node creation (just-in-time, not all upfront) ---
            exec_node = node_registry.create_exec_node(info.node_id)
            if exec_node is None:
                logger.warning(f"Cannot create execution node for: {info.node_id}")
                self.on_node_finished.emit(info.name, False)
                all_success = False
                continue
            self._exec_nodes[graph_node] = exec_node
            # -----------------------------------------------------------

            self.on_node_started.emit(info.name)
            self.on_progress.emit(i + 1, total)

            logger.info(f"Executing node: {info.name} ({info.node_id})")

            try:
                exec_node.params.update(info.param_values)
                exec_node.graph_node_name = graph_node.name()
                logger.info(f"  Params: {exec_node.params}")

                self._feed_input_data(graph_node, exec_node, info)

                success = exec_node.execute()

                self.on_node_finished.emit(info.name, success)

                if success:
                    # Emit incremental image output so viewer updates immediately
                    entries = self._get_image_entries_for_node(
                        graph_node, exec_node, info
                    )
                    if entries:
                        accumulated_entries.extend(entries)
                        self.on_image_output.emit(list(accumulated_entries))
                else:
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
            exec_port_name = info.resolve_port_name(graph_port_name)
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
                            src_info.resolve_port_name(src_port_name)
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

    def _get_image_entries_for_node(self, graph_node, exec_node, info):
        """Get all output entries from a node's output ports.

        Supports numpy arrays, ImageData, MathExpression, and MathMatrix.
        """
        entries = []
        for port in graph_node.output_ports():
            exec_port_name = info.resolve_port_name(port.name())
            exec_port = exec_node.get_output_port(exec_port_name)

            if exec_port is None:
                logger.warning(
                    f"  [{info.name}] Port '{port.name()}' -> exec port '{exec_port_name}' NOT FOUND"
                )
                continue

            if exec_port.data is None:
                logger.debug(
                    f"  [{info.name}] Port '{port.name()}' -> exec port '{exec_port_name}' data is None"
                )
                continue

            data = exec_port.data
            items = data if isinstance(data, list) else [data]

            # Image data
            images = [
                item for item in items
                if isinstance(item, (np.ndarray, ImageData))
            ]
            if images:
                logger.info(
                    f"  [{info.name}] Port '{port.name()}' -> '{exec_port_name}': "
                    f"{len(images)} images"
                )
                entry = ImageSetEntry(
                    name=f"{info.name}:{port.name()}",
                    images=images,
                )
                entries.append(entry)

            # Math expression data
            expressions = [
                item for item in items
                if isinstance(item, MathExpression)
            ]
            if expressions:
                logger.info(
                    f"  [{info.name}] Port '{port.name()}' -> '{exec_port_name}': "
                    f"{len(expressions)} expressions"
                )
                # Store expressions as text for display
                text_data = [e.text for e in expressions]
                entry = ImageSetEntry(
                    name=f"{info.name}:{port.name()}",
                    images=text_data,
                )
                entries.append(entry)

            # Matrix data
            matrices = [
                item for item in items
                if isinstance(item, MathMatrix)
            ]
            if matrices:
                logger.info(
                    f"  [{info.name}] Port '{port.name()}' -> '{exec_port_name}': "
                    f"{len(matrices)} matrices"
                )
                text_data = [str(m.matrix) for m in matrices]
                entry = ImageSetEntry(
                    name=f"{info.name}:{port.name()}",
                    images=text_data,
                )
                entries.append(entry)

        return entries

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

            entries = self._get_image_entries_for_node(graph_node, exec_node, info)
            for entry in entries:
                if not has_upstream:
                    input_sets.append(entry)
                if not has_downstream:
                    output_sets.append(entry)

        # Fallback: if output_sets is empty, walk upstream from terminal nodes
        # to find the nearest node that actually outputs images.
        if not output_sets:
            logger.info("Output sets empty, searching upstream for image data...")
            for graph_node in reversed(self._sorted_nodes):
                exec_node = self._exec_nodes.get(graph_node)
                info = self._node_infos.get(graph_node)
                if exec_node is None or info is None:
                    continue
                entries = self._get_image_entries_for_node(graph_node, exec_node, info)
                if entries:
                    logger.info(f"  Fallback found images from: {info.name}")
                    output_sets.extend(entries)
                    break

        # Fallback: if input_sets is empty, walk downstream from source nodes
        # to find the nearest node that actually outputs images.
        if not input_sets:
            logger.info("Input sets empty, searching downstream for image data...")
            for graph_node in self._sorted_nodes:
                exec_node = self._exec_nodes.get(graph_node)
                info = self._node_infos.get(graph_node)
                if exec_node is None or info is None:
                    continue
                entries = self._get_image_entries_for_node(graph_node, exec_node, info)
                if entries:
                    logger.info(f"  Fallback found images from: {info.name}")
                    input_sets.extend(entries)
                    break

        logger.info(
            f"Collected {len(input_sets)} input sets, "
            f"{len(output_sets)} output sets"
        )
        return ExecutionResult(
            success=success, input_sets=input_sets, output_sets=output_sets
        )
