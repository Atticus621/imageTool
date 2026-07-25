"""Node property panel — inline tabbed panel below the blueprint canvas.

Shows node parameters (editable) and node information (read-only) when
a node is selected. Reuses NodeParamPanel for parameter rendering and
NodeInfoWidget for port/connection display.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QFrame,
)

from core.logger import logger
from ui.theme import (
    BG_BASE, BG_SURFACE, BORDER_DEFAULT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_SIZE_SM, RADIUS_MD,
)
from ui.widgets.node_param_panel import NodeParamPanel
from ui.widgets.node_info_widget import NodeInfoWidget


class NodePropertyPanel(QWidget):
    """Inline panel below the blueprint canvas with two tabs.

    Tab 0 "参数": Editable parameter widgets (NodeParamPanel).
    Tab 1 "信息": Node details, port table, connection status (NodeInfoWidget).

    Signals:
        param_changed(str, object) — emitted when a param is modified.
            Payload: (param_name, new_value).
    """

    param_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_node = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER_DEFAULT};
                background-color: {BG_BASE};
                border-radius: {RADIUS_MD};
            }}
            QTabBar::tab {{
                background-color: {BG_SURFACE};
                color: {TEXT_SECONDARY};
                padding: 4px 12px;
                margin-right: 2px;
                border-top-left-radius: {RADIUS_MD};
                border-top-right-radius: {RADIUS_MD};
                font-size: {FONT_SIZE_SM};
            }}
            QTabBar::tab:selected {{
                background-color: {BG_BASE};
                color: {TEXT_PRIMARY};
                border-bottom: 2px solid {TEXT_PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {BG_BASE};
                color: {TEXT_PRIMARY};
            }}
        """)

        # Tab 0: Parameters (editable)
        self._param_panel = NodeParamPanel()
        self._param_scroll = self._wrap_in_scroll(self._param_panel)
        self._tab_widget.addTab(self._param_scroll, "参数")

        # Tab 1: Information (read-only)
        self._info_widget = NodeInfoWidget()
        self._tab_widget.addTab(self._info_widget, "信息")

        layout.addWidget(self._tab_widget)

        # Empty state placeholder (replaces tabs when nothing selected)
        self._empty_label = QLabel("选择一个节点以编辑参数和查看信息")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE_SM}; padding: 12px;"
            f"background-color: {BG_BASE}; border: 1px solid {BORDER_DEFAULT};"
            f"border-radius: {RADIUS_MD};"
        )
        layout.addWidget(self._empty_label)

        # Start with empty state
        self._tab_widget.hide()
        self._empty_label.show()

    def _wrap_in_scroll(self, widget: QWidget) -> QWidget:
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {BG_BASE}; border: none; }}"
        )
        scroll.setWidget(widget)
        return scroll

    def set_node(self, graph_node):
        """Switch to the given node, or show empty state if None."""
        self._current_node = graph_node

        if graph_node is None:
            self._tab_widget.hide()
            self._empty_label.show()
            return

        self._empty_label.hide()
        self._tab_widget.show()

        # Update parameters tab
        self._update_params(graph_node)

        # Update info tab
        self._info_widget.set_node(graph_node)

    def current_node(self):
        return self._current_node

    def _update_params(self, node):
        node_id = getattr(node, "_node_id", "")
        if not node_id:
            self._param_panel._clear()
            return

        try:
            from core.node_base.registry import node_registry
            meta = node_registry.get_meta(node_id)
        except Exception:
            meta = None

        if meta is None:
            self._param_panel._clear()
            return

        # Render params
        self._param_panel.set_target_node(node)
        self._param_panel.show_params(meta)

        # Fill current values
        param_values = getattr(node, "_param_values", {})
        self._param_panel.set_param_values(param_values)

        # Wire each param widget's value-changed signal
        self._wire_param_signals()

    def _wire_param_signals(self):
        """Connect each param widget's value-changed signal to our callback."""
        for name, (param, handler) in self._param_panel._param_widgets.items():
            signal = handler.get_value_changed_signal()
            if signal is not None:
                signal.connect(
                    lambda _unused=None, n=name, h=handler: self._on_param_changed(n, h.get_value())
                )

        # Wire optional port checkboxes
        for opc_name, checkbox in self._param_panel._optional_port_checkboxes.items():
            checkbox.stateChanged.connect(
                lambda _state=None, n=opc_name, cb=checkbox: self._on_optional_port_changed(n, cb.isChecked())
            )

    def _on_param_changed(self, param_name: str, value):
        """Called when a param widget changes value."""
        node = self._current_node
        if node is None:
            return

        # Write back to GraphNode immediately
        if hasattr(node, "_param_values"):
            node._param_values[param_name] = value

        # Sync optional port visibility
        if hasattr(node, "sync_port_visibility"):
            node.sync_port_visibility()

        # Notify listeners
        self.param_changed.emit(param_name, value)

        logger.debug(f"[PropertyPanel] Param changed: {param_name} = {value}")

    def _on_optional_port_changed(self, opc_name: str, visible: bool):
        """Called when an optional port checkbox changes."""
        node = self._current_node
        if node is None:
            return

        # Write back to GraphNode
        if hasattr(node, "_param_values"):
            node._param_values[f"_opt_{opc_name}"] = visible

        # Sync port visibility
        if hasattr(node, "set_optional_port_visible"):
            node.set_optional_port_visible(opc_name, visible)

        # Notify listeners
        self.param_changed.emit(f"_opt_{opc_name}", visible)
