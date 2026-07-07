import os

os.environ["QT_API"] = "pyside6"

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShortcut, QKeySequence
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
        self._embedded_widget = None

    def set_node_meta(self, meta):
        self._node_id = meta.id
        self.NODE_NAME = meta.name
        self.set_name(meta.name)

        self._port_label_to_name = {}
        self._port_count_groups: dict[str, list[str]] = {}  # count_param → [port_label, ...]
        self._optional_ports: dict[str, str] = {}  # opc_name → port_label

        for pdef in meta.inputs:
            port_name = pdef.label or pdef.name
            self.add_input(port_name, multi_input=True, display_name=True)
            self._port_label_to_name[port_name] = pdef.name

            if pdef.count_param:
                group = self._port_count_groups.setdefault(pdef.count_param, [])
                group.append(port_name)

        for pdef in meta.outputs:
            port_name = pdef.label or pdef.name
            self.add_output(port_name, multi_output=True, display_name=True)
            self._port_label_to_name[port_name] = pdef.name

        for p in meta.params:
            if p.default is not None:
                self._param_values[p.name] = p.default

        # ── 可选端口（预创建，默认隐藏） ──
        for opc in meta.optional_ports:
            port_label = opc.label or opc.name
            if opc.direction == "input":
                self.add_input(port_label, multi_input=True, display_name=True)
                port = self.get_input(port_label)
                if port:
                    port.set_visible(opc.default, push_undo=False)
            else:
                self.add_output(port_label, multi_output=True, display_name=True)
                port = self.get_output(port_label)
                if port:
                    port.set_visible(opc.default, push_undo=False)
            self._optional_ports[opc.name] = port_label
            self._port_label_to_name[port_label] = opc.name
            self._param_values[f"_opt_{opc.name}"] = opc.default

        # Apply initial visibility
        self._apply_port_count_visibility()

    def add_embedded_widget(self, widget):
        """Add an embedded widget (NodeBaseWidget) to this node."""
        self._embedded_widget = widget
        self.add_custom_widget(widget, widget_type=None)

    def get_embedded_widget(self):
        return self._embedded_widget

    def _apply_port_count_visibility(self):
        """Show/hide input ports based on count_param and current _param_values."""
        if not hasattr(self, '_port_count_groups'):
            return
        all_ports = self.inputs()
        for count_param, port_labels in self._port_count_groups.items():
            count = int(self._param_values.get(count_param, len(port_labels)))
            for i, label in enumerate(port_labels):
                if label in all_ports:
                    all_ports[label].set_visible(i < count, push_undo=False)

    def sync_port_visibility(self):
        """Public method called after _param_values is updated from UI."""
        self._apply_port_count_visibility()

    def set_optional_port_visible(self, opc_name: str, visible: bool):
        """实时显示/隐藏可选端口。

        Args:
            opc_name: 可选端口名称（如 "roi", "forbidden"）
            visible: 是否可见
        """
        port_label = self._optional_ports.get(opc_name)
        if not port_label:
            logger.warning(f"Optional port '{opc_name}' not found. Available: {list(self._optional_ports.keys())}")
            return

        # 尝试作为输入端口
        port = self.get_input(port_label)
        if port is None:
            # 尝试作为输出端口
            port = self.get_output(port_label)
        if port:
            port.set_visible(visible, push_undo=False)
            self._param_values[f"_opt_{opc_name}"] = visible
            logger.info(f"[GraphNode] Optional port '{opc_name}' ({port_label}) visibility -> {visible}, _param_values={self._param_values}")
        else:
            logger.warning(f"[GraphNode] Port object not found for '{opc_name}' (label='{port_label}')")

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
    node_delete_requested = Signal(object)
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

        self._setup_shortcuts()

        # Clipboard for copy/paste nodes: list of {node_id, params, x, y}
        self._clipboard: list[dict] = []

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
        nodes_menu.add_command(
            "删除节点",
            self._on_delete_node,
            node_type="imagetools.GraphNode",
        )

    def _make_create_node_action(self, node_id: str):
        def action(graph):
            pos = graph.cursor_pos()
            self._create_node_by_id(node_id, pos=pos, emit_signal=True)
        return action

    def _setup_shortcuts(self):
        """Register keyboard shortcuts for copy / paste / delete."""
        view = self._graph.viewer()
        # Delete / Backspace → delete selected nodes
        QShortcut(QKeySequence(Qt.Key_Delete), view, self._delete_selected_nodes)
        QShortcut(QKeySequence(Qt.Key_Backspace), view, self._delete_selected_nodes)
        # Ctrl+C → copy selected nodes
        QShortcut(QKeySequence.StandardKey.Copy, view, self._copy_selected_nodes)
        # Ctrl+V → paste copied node(s)
        QShortcut(QKeySequence.StandardKey.Paste, view, self._paste_nodes)

    # ── Delete ────────────────────────────────────────────────────────

    def _delete_selected_nodes(self):
        nodes = self._graph.selected_nodes()
        if not nodes:
            return
        for node in list(nodes):
            logger.info(f"Delete via shortcut: {node.name()}")
            self._graph.remove_node(node)

    # ── Copy / Paste ──────────────────────────────────────────────────

    def _copy_selected_nodes(self):
        nodes = self._graph.selected_nodes()
        if not nodes:
            return
        # Find the top-left anchor so pasted nodes keep relative layout
        min_x = min(n.x_pos() for n in nodes)
        min_y = min(n.y_pos() for n in nodes)

        self._clipboard = []
        for n in nodes:
            self._clipboard.append({
                "node_id": getattr(n, "_node_id", ""),
                "params": dict(getattr(n, "_param_values", {})),
                "dx": n.x_pos() - min_x,
                "dy": n.y_pos() - min_y,
            })
        logger.info(f"Copied {len(self._clipboard)} node(s) to clipboard")

    def _paste_nodes(self):
        if not self._clipboard:
            return
        cursor = self._graph.cursor_pos()
        cx, cy = cursor[0], cursor[1]

        for entry in self._clipboard:
            node_id = entry["node_id"]
            if not node_id:
                continue
            pos = (cx + entry["dx"], cy + entry["dy"])
            node = self._create_node_by_id(node_id, pos=pos, emit_signal=False)
            if node is not None and entry["params"]:
                node._param_values.update(entry["params"])
                node.sync_port_visibility()
        logger.info(f"Pasted {len(self._clipboard)} node(s) at cursor")

    def _on_create_empty_node(self, graph):
        logger.info("Create empty node requested")

    def _on_replace_node(self, graph, node):
        logger.info(f"Replace requested for: {node.name()}")
        self.node_replace_requested.emit(node)

    def _on_delete_node(self, graph, node):
        logger.info(f"Delete requested for: {node.name()}")
        self.node_delete_requested.emit(node)

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
