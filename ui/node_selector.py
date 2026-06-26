from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QScrollArea, QWidget, QGridLayout, QGroupBox,
    QLineEdit, QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFileDialog, QMessageBox, QFrame,
)

from core.logger import logger
from core.node_base.registry import node_registry
from core.node_base.node import ParamType


class NodeSelectorWindow(QDialog):
    node_type_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("节点选择")
        self.setMinimumSize(480, 550)
        self._target_node = None
        self._replace_mode = False
        self._edit_mode = False
        self._param_widgets = {}
        self._file_list_items = []
        self._file_list_layout = None
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
        self._file_list_items.clear()

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

                label = QLabel(param.label or param.name)
                group_layout.addWidget(label, row, 0)

                widget = self._create_param_widget(param)
                if widget:
                    group_layout.addWidget(widget, row, 1)
                    self._param_widgets[param.name] = (param, widget)
                row += 1

            for param in meta.params:
                if param.depends_on:
                    label = QLabel(param.label or param.name)
                    group_layout.addWidget(label, row, 0)
                    widget = self._create_param_widget(param)
                    if widget:
                        group_layout.addWidget(widget, row, 1)
                        self._param_widgets[param.name] = (param, widget)
                    row += 1

            self._param_layout.addWidget(group)

        self._param_layout.addStretch()

    def _create_param_widget(self, param):
        if param.param_type == ParamType.COMBO:
            combo = QComboBox()
            for opt in param.options:
                combo.addItem(opt.label, opt.value)

            if param.default is not None:
                idx = combo.findData(param.default)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            return combo

        elif param.param_type == ParamType.INT_SLIDER:
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            slider = QSlider(Qt.Orientation.Horizontal)
            spin = QSpinBox()
            slider.setMinimum(param.min_val or 0)
            slider.setMaximum(param.max_val or 100)
            slider.setSingleStep(param.step or 1)
            slider.setValue(param.default or 0)
            spin.setMinimum(param.min_val or 0)
            spin.setMaximum(param.max_val or 100)
            spin.setSingleStep(param.step or 1)
            spin.setValue(param.default or 0)
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            h.addWidget(slider)
            h.addWidget(spin)
            return container

        elif param.param_type == ParamType.FLOAT_SLIDER:
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            slider = QSlider(Qt.Orientation.Horizontal)
            dspin = QDoubleSpinBox()
            multiplier = 1000
            slider.setMinimum(int((param.min_val or 0) * multiplier))
            slider.setMaximum(int((param.max_val or 10) * multiplier))
            slider.setSingleStep(int((param.step or 0.01) * multiplier))
            slider.setValue(int((param.default or 0) * multiplier))
            dspin.setMinimum(param.min_val or 0)
            dspin.setMaximum(param.max_val or 10)
            dspin.setSingleStep(param.step or 0.01)
            dspin.setDecimals(3)
            dspin.setValue(param.default or 0)
            slider.valueChanged.connect(lambda v: dspin.setValue(v / multiplier))
            dspin.valueChanged.connect(lambda v: slider.setValue(int(v * multiplier)))
            h.addWidget(slider)
            h.addWidget(dspin)
            return container

        elif param.param_type == ParamType.TEXT:
            edit = QLineEdit()
            if param.default:
                edit.setText(str(param.default))
            return edit

        elif param.param_type == ParamType.CHECKBOX:
            cb = QCheckBox()
            cb.setChecked(bool(param.default))
            return cb

        elif param.param_type == ParamType.FILE_LIST:
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)

            list_container = QWidget()
            self._file_list_layout = QVBoxLayout(list_container)
            self._file_list_layout.setContentsMargins(0, 0, 0, 0)

            btn_row = QHBoxLayout()
            btn_add_file = QPushButton("+ 文件")
            btn_add_folder = QPushButton("+ 文件夹")
            btn_add_file.clicked.connect(lambda: self._add_file(param))
            btn_add_folder.clicked.connect(lambda: self._add_folder(param))
            btn_row.addWidget(btn_add_file)
            btn_row.addWidget(btn_add_folder)
            btn_row.addStretch()

            layout.addWidget(list_container)
            layout.addLayout(btn_row)

            self._file_list_widget = container
            self._file_list_container = list_container
            return container

        return None

    def _set_param_values(self, values: dict):
        for name, value in values.items():
            if name not in self._param_widgets:
                continue
            param, widget = self._param_widgets[name]

            if param.param_type == ParamType.COMBO:
                idx = widget.findData(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)

            elif param.param_type == ParamType.INT_SLIDER:
                spin = widget.findChild(QSpinBox)
                if spin:
                    spin.setValue(int(value))

            elif param.param_type == ParamType.FLOAT_SLIDER:
                dspin = widget.findChild(QDoubleSpinBox)
                if dspin:
                    dspin.setValue(float(value))

            elif param.param_type == ParamType.TEXT:
                widget.setText(str(value))

            elif param.param_type == ParamType.CHECKBOX:
                widget.setChecked(bool(value))

            elif param.param_type == ParamType.FILE_LIST:
                if isinstance(value, list):
                    for f in value:
                        self._add_file_item(f)

    def _add_file(self, param):
        filters = param.filters or "All Files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择图像文件", "", filters)
        for f in files:
            self._add_file_item(f)

    def _add_folder(self, param):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self._add_file_item(folder)

    def _add_file_item(self, path: str):
        item_widget = QWidget()
        h = QHBoxLayout(item_widget)
        h.setContentsMargins(0, 2, 0, 2)
        label = QLabel(path)
        label.setWordWrap(True)
        btn_remove = QPushButton("×")
        btn_remove.setMaximumWidth(30)
        btn_remove.clicked.connect(lambda: self._remove_file_item(item_widget))
        h.addWidget(label)
        h.addWidget(btn_remove)
        self._file_list_layout.addWidget(item_widget)
        self._file_list_items.append(item_widget)

    def _remove_file_item(self, widget):
        self._file_list_items.remove(widget)
        widget.deleteLater()

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

    def get_param_values(self) -> dict:
        values = {}
        for name, (param, widget) in self._param_widgets.items():
            if param.param_type == ParamType.COMBO:
                values[name] = widget.currentData()
            elif param.param_type == ParamType.INT_SLIDER:
                spin = widget.findChild(QSpinBox)
                if spin:
                    values[name] = spin.value()
            elif param.param_type == ParamType.FLOAT_SLIDER:
                dspin = widget.findChild(QDoubleSpinBox)
                if dspin:
                    values[name] = dspin.value()
            elif param.param_type == ParamType.TEXT:
                values[name] = widget.text()
            elif param.param_type == ParamType.CHECKBOX:
                values[name] = widget.isChecked()
            elif param.param_type == ParamType.FILE_LIST:
                files = []
                for item_widget in self._file_list_items:
                    label = item_widget.findChild(QLabel)
                    if label:
                        files.append(label.text())
                values[name] = files
        return values
