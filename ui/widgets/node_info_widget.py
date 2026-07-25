"""Node information widget — displays node details and port connection status.

Shows when a node is selected: node name, ID, category, description,
and a table of input/output ports with their types, connection status,
and connected peer nodes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout,
)

from ui.theme import (
    BG_BASE, BORDER_DEFAULT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ACCENT,
    FONT_SIZE_SM, SPACING_SM, SPACING_MD,
    PORT_COLORS,
)


class NodeInfoWidget(QWidget):
    """Displays detailed information about a selected node.

    Shows: node name/ID/category/description, input/output port table,
    and current parameter values (read-only).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_node = None
        self._init_ui()
        self._show_empty()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {BG_BASE}; border: none; }}"
        )

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(SPACING_SM)
        scroll.setWidget(self._content)

        # Placeholder for empty state
        self._placeholder = QLabel("选择一个节点以查看详情")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE_SM}; padding: 8px;"
        )

        layout.addWidget(scroll)

        # Header (node name + ID)
        self._header_label = QLabel()
        self._header_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-weight: bold; font-size: 13px;"
        )
        self._content_layout.addWidget(self._header_label)

        # Category + description
        self._meta_label = QLabel()
        self._meta_label.setWordWrap(True)
        self._meta_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SM};"
        )
        self._content_layout.addWidget(self._meta_label)

        # Separator
        self._sep1 = self._make_separator()
        self._content_layout.addWidget(self._sep1)

        # Input ports section
        self._input_title = QLabel("输入端口")
        self._input_title.setStyleSheet(
            f"color: {ACCENT}; font-size: {FONT_SIZE_SM}; font-weight: bold;"
        )
        self._content_layout.addWidget(self._input_title)

        self._input_ports_layout = QGridLayout()
        self._input_ports_layout.setSpacing(SPACING_SM)
        self._input_ports_widget = QWidget()
        self._input_ports_widget.setLayout(self._input_ports_layout)
        self._content_layout.addWidget(self._input_ports_widget)

        # Separator
        self._sep2 = self._make_separator()
        self._content_layout.addWidget(self._sep2)

        # Output ports section
        self._output_title = QLabel("输出端口")
        self._output_title.setStyleSheet(
            f"color: {ACCENT}; font-size: {FONT_SIZE_SM}; font-weight: bold;"
        )
        self._content_layout.addWidget(self._output_title)

        self._output_ports_layout = QGridLayout()
        self._output_ports_layout.setSpacing(SPACING_SM)
        self._output_ports_widget = QWidget()
        self._output_ports_widget.setLayout(self._output_ports_layout)
        self._content_layout.addWidget(self._output_ports_widget)

        # Separator
        self._sep3 = self._make_separator()
        self._content_layout.addWidget(self._sep3)

        # Parameters section (read-only)
        self._params_title = QLabel("当前参数")
        self._params_title.setStyleSheet(
            f"color: {ACCENT}; font-size: {FONT_SIZE_SM}; font-weight: bold;"
        )
        self._content_layout.addWidget(self._params_title)

        self._params_layout = QGridLayout()
        self._params_layout.setSpacing(SPACING_SM)
        self._params_widget = QWidget()
        self._params_widget.setLayout(self._params_layout)
        self._content_layout.addWidget(self._params_widget)

        self._content_layout.addStretch()

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER_DEFAULT};")
        return sep

    def set_node(self, graph_node):
        """Display information for the given node, or clear if None."""
        self._current_node = graph_node

        if graph_node is None:
            self._show_empty()
            return

        self._show_content()
        self._populate(graph_node)

    def _show_empty(self):
        self._header_label.hide()
        self._meta_label.hide()
        self._sep1.hide()
        self._input_title.hide()
        self._input_ports_widget.hide()
        self._sep2.hide()
        self._output_title.hide()
        self._output_ports_widget.hide()
        self._sep3.hide()
        self._params_title.hide()
        self._params_widget.hide()

    def _show_content(self):
        self._header_label.show()
        self._meta_label.show()
        self._sep1.show()
        self._input_title.show()
        self._input_ports_widget.show()
        self._sep2.show()
        self._output_title.show()
        self._output_ports_widget.show()
        self._sep3.show()
        self._params_title.show()
        self._params_widget.show()

    def _populate(self, node):
        node_id = getattr(node, "_node_id", "")
        name = node.name()

        # Header
        self._header_label.setText(f"{name}")
        if node_id:
            self._header_label.setText(f"{name}  ({node_id})")

        # Try to get meta for category/description
        try:
            from core.node_base.registry import node_registry
            meta = node_registry.get_meta(node_id) if node_id else None
        except Exception:
            meta = None

        if meta:
            cat = node_registry.get_category(node_id)
            subcat = node_registry.get_subcategory(node_id)
            desc = getattr(meta, "description", "")
            parts = []
            if cat:
                parts.append(cat)
            if subcat:
                parts.append(subcat)
            meta_text = " > ".join(parts)
            if desc:
                meta_text += f"\n{desc}" if meta_text else desc
            self._meta_label.setText(meta_text)
            self._meta_label.show()
        else:
            self._meta_label.hide()

        # Build port type lookup from meta (NodeGraphQt ports don't carry type info)
        port_type_map = {}  # {port_label: port_type_str}
        if meta:
            for pdef in meta.inputs:
                port_type_map[pdef.label or pdef.name] = pdef.port_type.value
            for pdef in meta.outputs:
                port_type_map[pdef.label or pdef.name] = pdef.port_type.value
            for opc in meta.optional_ports:
                port_type_map[opc.label or opc.name] = opc.port_type

        # Input ports
        self._populate_ports(
            self._input_ports_layout, node.input_ports(), "input", port_type_map
        )

        # Output ports
        self._populate_ports(
            self._output_ports_layout, node.output_ports(), "output", port_type_map
        )

        # Parameters (read-only view)
        self._populate_params(node)

    def _populate_ports(self, layout: QGridLayout, ports, direction: str,
                        port_type_map: dict[str, str] | None = None):
        # Clear existing rows
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not ports:
            no_ports = QLabel("无")
            no_ports.setStyleSheet(f"color: {TEXT_MUTED}; font-size: {FONT_SIZE_SM};")
            layout.addWidget(no_ports, 0, 0)
            return

        # Header row
        col_name = QLabel("端口")
        col_type = QLabel("类型")
        col_status = QLabel("状态")
        col_peer = QLabel("连接")

        for label in (col_name, col_type, col_status, col_peer):
            label.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SM}; font-weight: bold;"
            )
            label.setFixedHeight(18)

        layout.addWidget(col_name, 0, 0)
        layout.addWidget(col_type, 0, 1)
        layout.addWidget(col_status, 0, 2)
        layout.addWidget(col_peer, 0, 3)

        for i, port in enumerate(ports, start=1):
            port_name = port.name()

            # Get port type from meta lookup (NodeGraphQt ports don't carry type)
            port_type = ""
            if port_type_map and port_name in port_type_map:
                port_type = port_type_map[port_name]

            color = PORT_COLORS.get(port_type, TEXT_SECONDARY)

            name_label = QLabel(f"● {port_name}")
            name_label.setStyleSheet(
                f"color: {color}; font-size: {FONT_SIZE_SM};"
            )
            layout.addWidget(name_label, i, 0)

            type_label = QLabel(port_type or "—")
            type_label.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SM};"
            )
            layout.addWidget(type_label, i, 1)

            # Connection status
            connected_ports = port.connected_ports() if hasattr(port, "connected_ports") else []
            is_connected = len(connected_ports) > 0

            if is_connected:
                status_label = QLabel("● 已连接")
                status_label.setStyleSheet(
                    f"color: #34c759; font-size: {FONT_SIZE_SM};"
                )
            else:
                status_label = QLabel("○ 未连接")
                status_label.setStyleSheet(
                    f"color: {TEXT_MUTED}; font-size: {FONT_SIZE_SM};"
                )
            layout.addWidget(status_label, i, 2)

            # Peer node name
            if is_connected:
                peers = []
                for cp in connected_ports:
                    peer_node = cp.node() if hasattr(cp, "node") else None
                    peer_name = peer_node.name() if peer_node else "???"
                    peers.append(peer_name)
                peer_text = ", ".join(peers)
            else:
                peer_text = "—"

            peer_label = QLabel(peer_text)
            peer_label.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SM};"
            )
            peer_label.setWordWrap(True)
            layout.addWidget(peer_label, i, 3)

    def _populate_params(self, node):
        while self._params_layout.count():
            child = self._params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        param_values = getattr(node, "_param_values", {})
        if not param_values:
            no_params = QLabel("无参数")
            no_params.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: {FONT_SIZE_SM};"
            )
            self._params_layout.addWidget(no_params, 0, 0)
            return

        for i, (key, value) in enumerate(param_values.items()):
            key_label = QLabel(f"{key}:")
            key_label.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SM};"
            )
            self._params_layout.addWidget(key_label, i, 0)

            val_label = QLabel(str(value))
            val_label.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_SM};"
            )
            self._params_layout.addWidget(val_label, i, 1)
