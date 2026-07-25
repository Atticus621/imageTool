"""Node parameter editor panel — extracted from NodeSelectorWindow.

Renders input/output/advanced collapsible parameter groups for a
NodeMeta, with optional port checkboxes and dependency wiring.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget, QLabel,
    QFileDialog, QCheckBox,
)

from core.node_base.node import ParamType
from ui.param_widgets import create_param_widget, FileListParamWidget
from ui.widgets.collapsible_group_box import CollapsibleGroupBox
from core.logger import logger
from ui.theme import TEXT_PRIMARY, TEXT_MUTED


class NodeParamPanel(QWidget):
    """Renders editable parameter groups for a NodeMeta definition.

    Provides:
      - Collapsible input/output parameter groups (optional port checkboxes)
      - Flat "function parameters" group for Params
      - Dependency wiring between params
      - Value get/set

    Signals are NOT used — the owner reads values via get_param_values()
    and applies optional port changes via apply_optional_port_changes().
    """

    def __init__(self, dialog_parent=None, target_node=None):
        super().__init__()
        self._dialog_parent = dialog_parent
        self._target_node = target_node
        self._param_widgets: dict[str, tuple] = {}   # {name: (ParamDefinition, handler)}
        self._optional_port_checkboxes: dict[str, QCheckBox] = {}

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    # ── public API ──────────────────────────────────────────────────────

    def set_target_node(self, node):
        self._target_node = node

    def show_params(self, meta):
        """Render all parameter groups for the given NodeMeta as tabs."""
        self._clear()

        if meta is None:
            return

        info_label = QLabel(f"<b>{meta.name}</b><br>{meta.description}")
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self._layout.addWidget(info_label)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3a3b55;
                background: #222338;
            }
            QTabBar::tab {
                background: #2a2b40;
                color: #9898b0;
                padding: 4px 12px;
                margin-right: 1px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #32334a;
                color: #e8e8f0;
            }
            QTabBar::tab:hover {
                background: #3a3b55;
            }
        """)

        # Tab 1: Input ports
        input_opcs = [p for p in meta.optional_ports if p.direction == "input"]
        tabs.addTab(self._make_port_page(input_opcs, "无可配置输入端口"), "输入参数")

        # Tab 2: Function parameters
        if meta.params:
            tabs.addTab(self._make_params_page(meta), "函数参数")

        # Tab 3: Output ports
        output_opcs = [p for p in meta.optional_ports if p.direction == "output"]
        tabs.addTab(self._make_port_page(output_opcs, "无可配置输出端口"), "输出参数")

        # Tab 4: Advanced (placeholder)
        tabs.addTab(self._make_port_page([], "暂无高级参数"), "高级参数")

        self._layout.addWidget(tabs)
        self._layout.addStretch()

    def get_param_values(self) -> dict:
        values = {}
        for name, (param, handler) in self._param_widgets.items():
            values[name] = handler.get_value()
        return values

    def set_param_values(self, values: dict):
        """Set parameter values from a dict.

        Args:
            values: Dict mapping param names to values. Safe to pass None or empty dict.
        """
        if not values:
            return
        for name, value in values.items():
            handler = self._get_handler(name)
            if handler:
                handler.set_value(value)

    def apply_optional_port_changes(self):
        if not self._target_node or not hasattr(self._target_node, 'set_optional_port_visible'):
            return
        for opc_name, checkbox in self._optional_port_checkboxes.items():
            self._target_node.set_optional_port_visible(opc_name, checkbox.isChecked())

    # ── internal ────────────────────────────────────────────────────────

    def _clear(self):
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_widgets.clear()
        self._optional_port_checkboxes.clear()

    def _make_port_page(self, opcs, empty_text):
        """Create a page widget for optional port checkboxes."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        if opcs:
            for opc in opcs:
                self._add_optional_port_checkbox(opc, layout)
        else:
            lbl = QLabel(empty_text)
            lbl.setStyleSheet(f"color: {TEXT_MUTED};")
            layout.addWidget(lbl)
        layout.addStretch()
        return page

    def _make_params_group(self, meta):
        """Create a group widget for function parameters."""
        group = CollapsibleGroupBox("函数参数")
        group.setChecked(True)
        grid = QGridLayout(group)
        row = 0
        for param in meta.params:
            if not param.depends_on:
                row = self._add_param_row(param, grid, row)
        for param in meta.params:
            if param.depends_on:
                row = self._add_param_row(param, grid, row)
        group.finalize()
        return group

    def _add_optional_port_checkbox(self, opc, layout):
        current = opc.default
        if self._target_node and hasattr(self._target_node, '_param_values'):
            current = self._target_node._param_values.get(f"_opt_{opc.name}", opc.default)
        checkbox = QCheckBox(opc.label or opc.name)
        checkbox.setChecked(current)
        checkbox.setToolTip(f"控制是否启用 {opc.label} 端口（点确定后生效）")
        layout.addWidget(checkbox)
        self._optional_port_checkboxes[opc.name] = checkbox

    def _make_params_page(self, meta):
        """Create a page widget for function parameters."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        group = self._make_params_group(meta)
        layout.addWidget(group)
        layout.addStretch()
        self._wire_dependencies(meta)
        return page

    def _add_param_row(self, param, layout, row):
        handler = self._build_handler(param)
        if handler is None or handler.widget is None:
            return row + 1
        if handler.needs_own_label():
            layout.addWidget(handler.widget, row, 0, 1, 2)
        else:
            layout.addWidget(QLabel(param.label or param.name), row, 0)
            layout.addWidget(handler.widget, row, 1)
        self._param_widgets[param.name] = (param, handler)
        return row + 1

    def _build_handler(self, param):
        if param.param_type == ParamType.FILE_LIST:
            filters = param.filters or "All Files (*)"
            parent = self._dialog_parent or self
            handler = FileListParamWidget(
                param,
                add_file_callback=lambda _c=False, _n=param.name, _f=filters: self._on_add_files(_n, _f),
                add_folder_callback=lambda _c=False, _n=param.name: self._on_add_folder(_n),
            )
            handler.create_widget()
            return handler
        return create_param_widget(param)

    def _on_add_files(self, param_name, filters):
        if not param_name:
            logger.warning("File add callback received invalid parameter name")
            return
        parent = self._dialog_parent or self
        files, _ = QFileDialog.getOpenFileNames(parent, "选择图像文件", "", filters)
        handler = self._get_handler(param_name)
        if handler and files:
            for f in files:
                handler.add_file_item(f)

    def _on_add_folder(self, param_name):
        if not param_name:
            logger.warning("Folder add callback received invalid parameter name")
            return
        parent = self._dialog_parent or self
        folder = QFileDialog.getExistingDirectory(parent, "选择文件夹")
        handler = self._get_handler(param_name)
        if handler and folder:
            handler.add_file_item(folder)

    def _get_handler(self, param_name):
        entry = self._param_widgets.get(param_name)
        return entry[1] if entry else None

    def _wire_dependencies(self, meta):
        for name, (param, handler) in self._param_widgets.items():
            if not param.depends_on:
                continue
            source_name = param.depends_on
            if source_name not in self._param_widgets:
                continue
            _, source_handler = self._param_widgets[source_name]
            signal = source_handler.get_value_changed_signal()
            if signal is not None:
                signal.connect(
                    lambda _unused=None, h=handler, sn=source_name, sh=source_handler:
                        h.on_dependency_change(sn, sh.get_value())
                )
            handler.on_dependency_change(source_name, source_handler.get_value())
