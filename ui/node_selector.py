from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QScrollArea, QWidget, QGridLayout, QGroupBox,
    QFileDialog, QMessageBox, QFrame,
)

from core.logger import logger
from core.node_base.registry import node_registry
from core.node_base.node import ParamType
from ui.param_widgets import create_param_widget, FileListParamWidget


class NodeSelectorWindow(QDialog):
    node_type_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("节点选择")
        self.setMinimumSize(480, 550)
        self._target_node = None
        self._replace_mode = False
        self._edit_mode = False
        self._param_widgets: dict[str, tuple] = {}  # {name: (ParamDefinition, ParamWidget)}
        self._current_meta = None
        self._init_ui()
        self._populate_category()
        logger.info("NodeSelectorWindow initialized")

    def set_target_node(self, node):
        self._target_node = node

    def set_replace_mode(self, enabled: bool):
        self._replace_mode = enabled
        if enabled:
            self.setWindowTitle("替换节点")
            self._btn_ok.setText("替换")
        else:
            self.setWindowTitle("节点选择")
            self._btn_ok.setText("确定")

    def set_edit_mode(self, enabled: bool):
        self._edit_mode = enabled
        if enabled:
            self.setWindowTitle("编辑节点")
            self._btn_ok.setText("确定")

    def preselect_node(self, node_id: str, param_values: dict = None):
        meta = node_registry.get_meta(node_id)
        if meta is None:
            return

        self._combo_category.blockSignals(True)
        self._combo_subcategory.blockSignals(True)
        self._combo_node.blockSignals(True)

        cat = meta.category
        idx = self._combo_category.findData(cat)
        if idx >= 0:
            self._combo_category.setCurrentIndex(idx)

        self._combo_subcategory.clear()
        tree = node_registry.get_category_tree()
        subs = tree.get(cat, {})
        sub_keys = [k for k in subs.keys() if k != "_items"]

        has_direct = "_items" in subs and subs["_items"]
        if not sub_keys and has_direct:
            self._combo_subcategory.addItem("--", "__direct__")
        else:
            self._combo_subcategory.addItem("-- 请选择 --", "")
            for sub in sorted(sub_keys):
                self._combo_subcategory.addItem(sub, sub)

        if meta.subcategory:
            idx = self._combo_subcategory.findData(meta.subcategory)
            if idx >= 0:
                self._combo_subcategory.setCurrentIndex(idx)
        elif has_direct and not sub_keys:
            self._combo_subcategory.setCurrentIndex(0)

        self._combo_node.clear()
        sub = self._combo_subcategory.currentData()
        if sub == "__direct__":
            items = subs.get("_items", [])
        elif sub:
            items = subs.get(sub, [])
        else:
            items = []

        self._combo_node.addItem("-- 请选择 --", "")
        for item_meta in items:
            self._combo_node.addItem(item_meta.name, item_meta.id)

        idx = self._combo_node.findData(node_id)
        if idx >= 0:
            self._combo_node.setCurrentIndex(idx)

        self._combo_category.blockSignals(False)
        self._combo_subcategory.blockSignals(False)
        self._combo_node.blockSignals(False)

        self._show_params(meta)

        if param_values:
            self._set_param_values(param_values)

        self._btn_ok.setEnabled(True)
        self._current_meta = meta

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        dropdown_group = QGroupBox("节点类型")
        dropdown_layout = QGridLayout(dropdown_group)

        dropdown_layout.addWidget(QLabel("分类:"), 0, 0)
        self._combo_category = QComboBox()
        self._combo_category.currentIndexChanged.connect(self._on_category_changed)
        dropdown_layout.addWidget(self._combo_category, 0, 1)

        dropdown_layout.addWidget(QLabel("子分类:"), 1, 0)
        self._combo_subcategory = QComboBox()
        self._combo_subcategory.currentIndexChanged.connect(self._on_subcategory_changed)
        dropdown_layout.addWidget(self._combo_subcategory, 1, 1)

        dropdown_layout.addWidget(QLabel("节点:"), 2, 0)
        self._combo_node = QComboBox()
        self._combo_node.currentIndexChanged.connect(self._on_node_changed)
        dropdown_layout.addWidget(self._combo_node, 2, 1)

        layout.addWidget(dropdown_group)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self._param_area = QScrollArea()
        self._param_area.setWidgetResizable(True)
        self._param_widget = QWidget()
        self._param_layout = QVBoxLayout(self._param_widget)
        self._param_area.setWidget(self._param_widget)
        layout.addWidget(self._param_area, 1)

        self._info_label = QLabel("请选择节点类型")
        self._info_label.setWordWrap(True)
        self._info_label.setStyleSheet("color: gray; padding: 20px;")
        self._param_layout.addWidget(self._info_label)
        self._param_layout.addStretch()

        btn_layout = QHBoxLayout()
        self._btn_ok = QPushButton("确定")
        self._btn_cancel = QPushButton("取消")
        self._btn_ok.setEnabled(False)
        self._btn_ok.clicked.connect(self._on_ok)
        self._btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_ok)
        btn_layout.addWidget(self._btn_cancel)
        layout.addLayout(btn_layout)

    def _populate_category(self):
        self._combo_category.blockSignals(True)
        self._combo_category.clear()
        self._combo_category.addItem("-- 请选择 --", "")

        tree = node_registry.get_category_tree()
        for cat in sorted(tree.keys()):
            self._combo_category.addItem(cat, cat)

        self._combo_category.blockSignals(False)
        self._combo_subcategory.clear()
        self._combo_node.clear()

    def _on_category_changed(self, index):
        self._combo_subcategory.blockSignals(True)
        self._combo_subcategory.clear()
        self._combo_node.clear()
        self._btn_ok.setEnabled(False)

        cat = self._combo_category.currentData()
        if not cat:
            self._combo_subcategory.blockSignals(False)
            return

        tree = node_registry.get_category_tree()
        subs = tree.get(cat, {})

        has_direct_items = "_items" in subs and subs["_items"]
        sub_keys = [k for k in subs.keys() if k != "_items"]

        if not sub_keys and has_direct_items:
            self._combo_subcategory.addItem("--", "__direct__")
            self._combo_subcategory.blockSignals(False)
            self._on_subcategory_changed(0)
            return

        self._combo_subcategory.addItem("-- 请选择 --", "")
        for sub in sorted(sub_keys):
            self._combo_subcategory.addItem(sub, sub)

        self._combo_subcategory.blockSignals(False)

    def _on_subcategory_changed(self, index):
        self._combo_node.blockSignals(True)
        self._combo_node.clear()
        self._btn_ok.setEnabled(False)

        cat = self._combo_category.currentData()
        sub = self._combo_subcategory.currentData()
        if not cat:
            self._combo_node.blockSignals(False)
            return

        tree = node_registry.get_category_tree()
        subs = tree.get(cat, {})

        if sub == "__direct__":
            items = subs.get("_items", [])
        elif sub:
            items = subs.get(sub, [])
        else:
            self._combo_node.blockSignals(False)
            return

        self._combo_node.addItem("-- 请选择 --", "")
        for meta in items:
            self._combo_node.addItem(meta.name, meta.id)

        self._combo_node.blockSignals(False)

    def _on_node_changed(self, index):
        node_id = self._combo_node.currentData()
        if not node_id:
            self._btn_ok.setEnabled(False)
            self._clear_params()
            self._info_label = QLabel("请选择节点类型")
            self._info_label.setWordWrap(True)
            self._info_label.setStyleSheet("color: gray; padding: 20px;")
            self._param_layout.addWidget(self._info_label)
            return

        meta = node_registry.get_meta(node_id)
        if meta:
            self._show_params(meta)
            self._btn_ok.setEnabled(True)
            self._current_meta = meta

    def _clear_params(self):
        while self._param_layout.count():
            child = self._param_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_widgets.clear()

    # ── Parameter rendering ──────────────────────────────────────────

    def _show_params(self, meta):
        self._clear_params()

        info_label = QLabel(f"<b>{meta.name}</b><br>{meta.description}")
        info_label.setWordWrap(True)
        self._param_layout.addWidget(info_label)

        if meta.params:
            group = QGroupBox("函数参数")
            group_layout = QGridLayout(group)
            row = 0

            for param in meta.params:
                if param.depends_on:
                    continue
                row = self._add_param_row(param, group_layout, row)

            for param in meta.params:
                if param.depends_on:
                    row = self._add_param_row(param, group_layout, row)

            self._param_layout.addWidget(group)

            # Generic dependency wiring (replaces hard-coded _wire_channel_type_dependency)
            self._wire_dependencies(meta)

        self._param_layout.addStretch()

    def _add_param_row(self, param, layout: QGridLayout, row: int) -> int:
        """Create a ParamWidget handler and add its widget to the grid.

        For regular params: [QLabel | widget]
        For self-labeling params (CHANNEL_RANGE): [widget spans both columns]
        """
        handler = self._build_handler(param)
        if handler is None:
            return row + 1

        widget = handler.widget
        if widget is None:
            return row + 1

        if handler.needs_own_label():
            layout.addWidget(widget, row, 0, 1, 2)
        else:
            label = QLabel(param.label or param.name)
            layout.addWidget(label, row, 0)
            layout.addWidget(widget, row, 1)

        self._param_widgets[param.name] = (param, handler)
        return row + 1

    def _build_handler(self, param):
        """Build a ParamWidget handler for a parameter definition.

        FILE_LIST needs special treatment: its callbacks require the dialog
        parent (self). All other types use the standard factory.
        """
        if param.param_type == ParamType.FILE_LIST:
            filters = param.filters or "All Files (*)"
            handler = FileListParamWidget(
                param,
                add_file_callback=lambda: self._on_add_files(param, filters),
                add_folder_callback=lambda: self._on_add_folder(param),
            )
            handler.create_widget()
            return handler

        return create_param_widget(param)

    # ── FileList callbacks (dialog parent = self) ───────────────────

    def _on_add_files(self, param, filters: str):
        files, _ = QFileDialog.getOpenFileNames(self, "选择图像文件", "", filters)
        handler = self._get_handler(param.name)
        if handler and files:
            for f in files:
                handler.add_file_item(f)

    def _on_add_folder(self, param):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        handler = self._get_handler(param.name)
        if handler and folder:
            handler.add_file_item(folder)

    def _get_handler(self, param_name: str):
        """Get the ParamWidget handler for a parameter name."""
        entry = self._param_widgets.get(param_name)
        return entry[1] if entry else None

    # ── Generic dependency wiring ───────────────────────────────────

    def _wire_dependencies(self, meta):
        """Connect source param signals to dependent param callbacks.

        For each parameter P where p.depends_on is set:
          1. Find the source handler Q whose name matches p.depends_on.
          2. Connect Q's value_changed_signal → P's on_dependency_change.
          3. Fire an initial sync so P starts in the correct state.
        """
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

            # Initial sync
            handler.on_dependency_change(source_name, source_handler.get_value())

    # ── Value read / write (delegated to handlers) ──────────────────

    def _set_param_values(self, values: dict):
        for name, value in values.items():
            handler = self._get_handler(name)
            if handler:
                handler.set_value(value)

    def get_param_values(self) -> dict:
        values = {}
        for name, (param, handler) in self._param_widgets.items():
            values[name] = handler.get_value()
        return values

    # ── OK / Replace ────────────────────────────────────────────────

    def _on_ok(self):
        node_id = self._combo_node.currentData()
        if not node_id:
            return

        if self._replace_mode and self._target_node:
            self._do_replace(node_id)
        else:
            self.node_type_selected.emit(node_id)

        self.accept()

    def _do_replace(self, new_node_id: str):
        target = self._target_node
        if target is None:
            return

        old_meta_id = getattr(target, "_node_id", "")
        old_meta = node_registry.get_meta(old_meta_id)
        new_meta = node_registry.get_meta(new_node_id)

        if old_meta is None or new_meta is None:
            logger.error(f"Cannot replace: meta not found")
            return

        if old_meta.category != new_meta.category:
            QMessageBox.warning(self, "替换失败", "只能替换同类型的节点")
            return

        logger.info(f"Replacing node: {old_meta.name} -> {new_meta.name}")
        self.node_type_selected.emit(new_node_id)

    def get_selected_node_id(self) -> str:
        return self._combo_node.currentData() or ""
