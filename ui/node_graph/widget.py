"""NodeGraphWidget — Qt widget wrapping a NodeGraphQt canvas."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QInputDialog

from NodeGraphQt import NodeGraph, GroupNode
from NodeGraphQt.nodes.port_node import PortInputNode, PortOutputNode
from NodeGraphQt.qgraphics.node_base import NodeTextItem

from core.logger import logger
from core.node_base.registry import node_registry
from ui.adapters.node_graph_workarounds import apply_double_click_unlock_patch
from ui.node_graph.graph_node import GraphNode
from ui.node_graph.clipboard_manager import ClipboardManager
from ui.node_graph.shortcut_handler import ShortcutHandler
from ui.node_graph.context_menu_builder import ContextMenuBuilder


class NodeGraphWidget(QWidget):
    """Qt widget that owns and manages a NodeGraphQt canvas.

    Responsibilities (graphics only):
      - Create / delete / replace nodes on the canvas
      - Provide context menus for node creation
      - Manage clipboard (copy/paste) and keyboard shortcuts
      - Create sub-blueprints and port nodes
      - Provide inline node rename

    Business logic (what to do on events) is NOT handled here —
    use signals to notify handlers/controllers.
    """

    # Signals emitted upward to business-logic handlers
    node_replace_requested = Signal(object)
    node_delete_requested = Signal(object)
    node_created_with_meta = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._graph: NodeGraph | None = None
        self._clipboard = ClipboardManager()
        self._init_ui()
        logger.info("NodeGraphWidget initialized")

    def _init_ui(self):
        apply_double_click_unlock_patch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._graph = NodeGraph()
        self._graph.register_node(GraphNode)
        self._graph.register_node(GroupNode)
        self._graph.register_node(PortInputNode)
        self._graph.register_node(PortOutputNode)
        self._graph.set_acyclic(True)
        self._graph.set_pipe_collision(True)
        self._graph.set_pipe_slicing(False)
        self._graph.set_background_color(35, 35, 50)

        self._menu_builder = ContextMenuBuilder(
            node_registry, self._create_node_by_id)
        self._setup_context_menu()
        layout.addWidget(self._graph.widget)
        self._setup_shortcuts()

    # ── context menu ─────────────────────────────────────────────────────

    def _setup_context_menu(self):
        graph_menu = self._graph.get_context_menu("graph")
        graph_menu.add_separator()
        graph_menu.add_command("创建子蓝图", self._on_create_sub_blueprint)
        graph_menu.add_separator()

        tree = node_registry.get_category_tree()
        self._menu_builder.build_menu_from_tree(graph_menu, tree)

        nodes_menu = self._graph.get_context_menu("nodes")
        nodes_menu.add_separator()
        nodes_menu.add_command("重命名", self._on_rename_node,
                               node_type="nodeGraphQt.nodes.GroupNode")
        nodes_menu.add_command("重命名端口", self._on_rename_node,
                               node_type="nodeGraphQt.nodes.PortInputNode")
        nodes_menu.add_command("重命名端口", self._on_rename_node,
                               node_type="nodeGraphQt.nodes.PortOutputNode")
        nodes_menu.add_command("替换节点", self._on_replace_node,
                               node_type="imagetools.GraphNode")
        nodes_menu.add_command("删除节点", self._on_delete_node,
                               node_type="imagetools.GraphNode")

    # ── shortcuts ────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        ShortcutHandler(
            self._graph.viewer(),
            on_delete=self._delete_selected_nodes,
            on_copy=self._copy_selected_nodes,
            on_paste=self._paste_nodes,
        )

    # ── delete / copy / paste ────────────────────────────────────────────

    def _delete_selected_nodes(self):
        nodes = self._graph.selected_nodes()
        if not nodes:
            return
        for node in list(nodes):
            logger.info(f"Delete via shortcut: {node.name()}")
            self._graph.remove_node(node)

    def _copy_selected_nodes(self):
        nodes = self._graph.selected_nodes()
        self._clipboard.copy_nodes(nodes)

    def _paste_nodes(self):
        entries = self._clipboard.paste_entries()
        if not entries:
            return
        cursor = self._graph.cursor_pos()
        cx, cy = cursor[0], cursor[1]
        for entry in entries:
            node_id = entry["node_id"]
            if not node_id:
                continue
            pos = (cx + entry["dx"], cy + entry["dy"])
            node = self._create_node_by_id(node_id, pos=pos, emit_signal=False)
            if node is not None and entry["params"]:
                node._param_values.update(entry["params"])
                node.sync_port_visibility()
        logger.info(f"Pasted {len(entries)} node(s) at cursor")

    # ── sub-blueprint ────────────────────────────────────────────────────

    def _on_create_sub_blueprint(self, graph):
        logger.info("Create sub-blueprint node requested")
        pos = graph.cursor_pos()
        try:
            node = graph.create_node(
                "nodeGraphQt.nodes.GroupNode", name="子蓝图", pos=pos,
            )
            for i in range(1, 3):
                node.add_input(f"输入{i}", multi_input=True, display_name=True)
            for i in range(1, 3):
                node.add_output(f"输出{i}", multi_output=True, display_name=True)
            node.view.draw_node()
            logger.info(f"Created sub-blueprint node at {pos}")
            return node
        except Exception as e:
            logger.error(f"Failed to create sub-blueprint node: {e}")
            return None

    def _on_add_input_port(self, graph):
        from NodeGraphQt import SubGraph
        if isinstance(graph, SubGraph):
            group_node = graph.node
            cnt = len(group_node.input_ports()) + 1
            group_node.add_input(f"输入{cnt}", multi_input=True, display_name=True)
            group_node.view.draw_node()
        else:
            logger.warning(
                "_on_add_input_port called outside SubGraph — ignoring"
            )

    def _on_add_output_port(self, graph):
        from NodeGraphQt import SubGraph
        if isinstance(graph, SubGraph):
            group_node = graph.node
            cnt = len(group_node.output_ports()) + 1
            group_node.add_output(f"输出{cnt}", multi_output=True, display_name=True)
            group_node.view.draw_node()
        else:
            logger.warning(
                "_on_add_output_port called outside SubGraph — ignoring"
            )

    def setup_sub_graph_menu(self, sub_graph):
        """Add SubGraph-only context menu items (port add/remove).

        SubGraph clones the parent graph's context menu on creation
        (see graph.py:_clone_context_menu_from_parent).  "添加输入端口"
        and "添加输出端口" are deliberately omitted from the root graph
        menu and added here so they only appear inside sub-blueprints.
        """
        graph_menu = sub_graph.get_context_menu("graph")
        # Guard: don't add duplicates if called multiple times
        existing = {item.name() for item in graph_menu.get_items()
                    if item is not None}
        if "添加输入端口" not in existing:
            graph_menu.add_command("添加输入端口", self._on_add_input_port)
            graph_menu.add_command("添加输出端口", self._on_add_output_port)
            logger.info(f"SubGraph menu configured for '{sub_graph.node.name()}'")

    # ── rename ───────────────────────────────────────────────────────────

    def _on_rename_node(self, graph, node):
        self.rename_node_inline(node)

    def rename_node_inline(self, node):
        view = node.view
        for item in view.childItems():
            if isinstance(item, NodeTextItem):
                item.set_locked(False)
                item.set_editable(True)
                item.setFocus()
                logger.info(f"Enabled inline editing for: {node.name()}")
                return
        old_name = node.name()
        new_name, ok = QInputDialog.getText(
            self, "重命名节点", "节点名称:", text=old_name,
        )
        if ok and new_name and new_name != old_name:
            node.set_name(new_name)
            logger.info(f"Renamed node: {old_name} -> {new_name}")

    # ── replace / delete signals ─────────────────────────────────────────

    def _on_replace_node(self, graph, node):
        self.node_replace_requested.emit(node)

    def _on_delete_node(self, graph, node):
        self.node_delete_requested.emit(node)

    # ── node CRUD ────────────────────────────────────────────────────────

    def create_node_by_id(self, node_id: str, pos=None):
        return self._create_node_by_id(node_id, pos=pos)

    def _create_node_by_id(self, node_id: str, graph=None, pos=None,
                           emit_signal=True):
        meta = node_registry.get_meta(node_id)
        if meta is None:
            logger.error(f"Node type not found: {node_id}")
            return None
        target_graph = graph or self._graph
        node = target_graph.create_node(
            "imagetools.GraphNode", name=meta.name, pos=pos,
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
            return None
        old_meta_id = getattr(old_node, "_node_id", "")
        old_meta = node_registry.get_meta(old_meta_id)
        if old_meta and old_meta.category != meta.category:
            logger.warning(
                f"Cannot replace: category mismatch "
                f"({old_meta.category} != {meta.category})"
            )
            return None

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
            "imagetools.GraphNode", name=meta.name, pos=pos,
        )
        new_node.set_node_meta(meta)

        new_inputs = new_node.inputs()
        for port_name, src_ports in input_connections.items():
            if port_name in new_inputs:
                for src_port in src_ports:
                    try:
                        src_port.connect_to(new_inputs[port_name], push_undo=False)
                    except Exception as e:
                        logger.warning(
                            f"Failed to restore input connection {port_name}: {e}"
                        )

        new_outputs = new_node.outputs()
        for port_name, dst_ports in output_connections.items():
            if port_name in new_outputs:
                for dst_port in dst_ports:
                    try:
                        new_outputs[port_name].connect_to(dst_port, push_undo=False)
                    except Exception as e:
                        logger.warning(
                            f"Failed to restore output connection {port_name}: {e}"
                        )

        logger.info(f"Replaced node: {old_meta_id} -> {new_node_id}")
        return new_node

    @property
    def graph(self) -> NodeGraph:
        return self._graph

    def get_all_graph_nodes(self) -> list:
        return self._graph.all_nodes()
