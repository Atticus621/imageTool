import os

os.environ["QT_API"] = "pyside6"

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from NodeGraphQt import NodeGraph, BaseNode

from core.logger import logger
from core.node_base.registry import node_registry
from core.pipeline import PipelineNodeInfo


class GraphNode(BaseNode):
    __identifier__ = "imagetools"

    NODE_NAME = "GraphNode"

    def __init__(self):
        super().__init__()
        self._node_id = ""
        self._input_image_count = 0
        self._output_image_count = 0
        self._state = "idle"
        self._param_values = {}

    def set_node_meta(self, meta):
        self._node_id = meta.id
        self.NODE_NAME = meta.name
        self.set_name(meta.name)

        self._port_label_to_name = {}

        for pdef in meta.inputs:
            port_name = pdef.label or pdef.name
            self.add_input(port_name, multi_input=True, display_name=True)
            self._port_label_to_name[port_name] = pdef.name

        for pdef in meta.outputs:
            port_name = pdef.label or pdef.name
            self.add_output(port_name, multi_output=True, display_name=True)
            self._port_label_to_name[port_name] = pdef.name

        for p in meta.params:
            if p.default is not None:
                self._param_values[p.name] = p.default

    def update_state_color(self, state: str):
        self._state = state
        colors = {
            "idle": (128, 128, 128),
            "running": (255, 200, 0),
            "success": (0, 200, 0),
            "error": (220, 50, 50),
        }
        color = colors.get(state, (128, 128, 128))
        self.set_color(*color)

    def to_pipeline_info(self) -> PipelineNodeInfo:
        return PipelineNodeInfo(
            node_id=self._node_id,
            name=self.name(),
            param_values=dict(self._param_values),
            port_label_to_name=dict(getattr(self, "_port_label_to_name", {})),
        )

    def get_input_image_count(self) -> int:
        count = 0
        for port in self.input_ports():
            if not port.connected_ports():
                count += 1
        return count

    def get_output_image_count(self) -> int:
        count = 0
        for port in self.output_ports():
            if not port.connected_ports():
                count += 1
        return count


class NodeGraphWidget(QWidget):
    node_replace_requested = Signal(object)
    node_created_with_meta = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._graph = None
        self._init_ui()
        logger.info("NodeGraphWidget initialized")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._graph = NodeGraph()
        self._graph.register_node(GraphNode)

        self._graph.set_acyclic(True)
        self._graph.set_pipe_collision(True)
        self._graph.set_pipe_slicing(False)

        self._graph.set_background_color(35, 35, 50)

        self._setup_context_menu()

        viewer = self._graph.viewer()
        layout.addWidget(viewer)

    def _setup_context_menu(self):
        context_menu = self._graph.get_context_menu("graph")

        context_menu.add_separator()
        context_menu.add_command("创建空白节点", self._on_create_empty_node)
        context_menu.add_separator()

        for cat, subs in node_registry.get_category_tree().items():
            cat_menu = context_menu.add_menu(cat)
            for sub, items in subs.items():
                if sub == "_items":
                    for meta in items:
                        cat_menu.add_command(
                            meta.name,
                            self._make_create_node_action(meta.id),
                        )
                else:
                    sub_menu = cat_menu.add_menu(sub)
                    for meta in items:
                        sub_menu.add_command(
                            meta.name,
                            self._make_create_node_action(meta.id),
                        )

        nodes_menu = self._graph.get_context_menu("nodes")
        nodes_menu.add_separator()
        nodes_menu.add_command(
            "替换节点",
            self._on_replace_node,
            node_type="imagetools.GraphNode",
        )

    def _make_create_node_action(self, node_id: str):
        def action(graph):
            pos = graph.cursor_pos()
            self._create_node_by_id(node_id, pos=pos, emit_signal=True)
        return action

    def _on_create_empty_node(self, graph):
        logger.info("Create empty node requested")

    def _on_replace_node(self, graph, node):
        logger.info(f"Replace requested for: {node.name()}")
        self.node_replace_requested.emit(node)

    def create_node_by_id(self, node_id: str, pos=None):
        return self._create_node_by_id(node_id, pos=pos)

    def _create_node_by_id(self, node_id: str, pos=None, emit_signal=True):
        meta = node_registry.get_meta(node_id)
        if meta is None:
            logger.error(f"Node type not found: {node_id}")
            return

        node = self._graph.create_node(
            f"imagetools.GraphNode",
            name=meta.name,
            pos=pos,
        )
        node.set_node_meta(meta)
        logger.info(f"Created node: {meta.name} ({node_id}) at {pos}")
        if emit_signal:
            self.node_created_with_meta.emit(node, node_id)
        return node

    def replace_node(self, old_node, new_node_id: str):
        meta = node_registry.get_meta(new_node_id)
        if meta is None:
            logger.error(f"Node type not found: {new_node_id}")
            return

        old_meta_id = getattr(old_node, "_node_id", "")
        old_meta = node_registry.get_meta(old_meta_id)

        if old_meta and old_meta.category != meta.category:
            logger.warning(f"Cannot replace: category mismatch ({old_meta.category} != {meta.category})")
            return

        input_connections = {}
        for port in old_node.input_ports():
            connected = port.connected_ports()
            if connected:
                input_connections[port.name()] = list(connected)

        output_connections = {}
        for port in old_node.output_ports():
            connected = port.connected_ports()
            if connected:
                output_connections[port.name()] = list(connected)

        pos = old_node.pos()

        self._graph.remove_node(old_node)

        new_node = self._graph.create_node(
            f"imagetools.GraphNode",
            name=meta.name,
            pos=pos,
        )
        new_node.set_node_meta(meta)

        new_inputs = new_node.inputs()
        for port_name, src_ports in input_connections.items():
            if port_name in new_inputs:
                for src_port in src_ports:
                    try:
                        src_port.connect_to(new_inputs[port_name], push_undo=False)
                    except Exception as e:
                        logger.warning(f"Failed to restore input connection {port_name}: {e}")

        new_outputs = new_node.outputs()
        for port_name, dst_ports in output_connections.items():
            if port_name in new_outputs:
                for dst_port in dst_ports:
                    try:
                        new_outputs[port_name].connect_to(dst_port, push_undo=False)
                    except Exception as e:
                        logger.warning(f"Failed to restore output connection {port_name}: {e}")

        logger.info(f"Replaced node: {old_meta_id} -> {new_node_id}")
        return new_node

    @property
    def graph(self) -> NodeGraph:
        return self._graph

    def get_all_graph_nodes(self) -> list:
        return self._graph.all_nodes()
