# -*- coding: utf-8 -*-
"""处理对话框 —— QDialog: 从 PROCESS_PRESETS + PARAM_RANGES 动态构建表单。

PROCESS_PRESETS 支持任意深度嵌套：
  - 类别节点: dict 不含 "func" key，值为子节点 dict
  - 叶子节点: dict 包含 "func" key 和 "params" key
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLabel, QSlider, QDoubleSpinBox, QSpinBox,
    QPushButton, QScrollArea, QWidget, QCheckBox, QGroupBox,
)


def _is_leaf(node: dict) -> bool:
    """判断节点是否为叶子（包含 func key）。"""
    return isinstance(node, dict) and "func" in node


class ProcessingDialog(QDialog):
    """图像处理参数调节对话框。"""

    add_requested = Signal(str, dict)       # func_name, params
    preview_requested = Signal(str, dict)   # func_name, params
    selection_changed = Signal(str, str, dict)  # display_name, func_name, params

    def __init__(self, presets, param_ranges,
                 preview_callback=None, close_callback=None,
                 edit_mode=False, edit_func_name=None, edit_params=None,
                 roi_regions=None, adaptive_callback=None, kmeans_callback=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑处理步骤" if edit_mode else "添加处理步骤")
        self.resize(420, 600)
        self.setMinimumWidth(380)

        self._presets = presets
        self._param_ranges = param_ranges
        self._preview_callback = preview_callback
        self._close_callback = close_callback
        self._edit_mode = edit_mode
        self._edit_func_name = edit_func_name
        self._edit_params = edit_params if edit_params else {}
        self._edit_complete_callback = None
        self._roi_regions = roi_regions if roi_regions else []
        self._adaptive_callback = adaptive_callback
        self._kmeans_callback = kmeans_callback
        self._widgets = {}

        # 动态 combo 框列表
        self._combos = []
        self._combo_container = QVBoxLayout()

        self._build_ui()

    def set_edit_complete_callback(self, cb):
        self._edit_complete_callback = cb

    # ── UI ──
    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 动态类别导航区
        layout.addLayout(self._combo_container)

        # 参数滚动区（必须在 combo 初始化前创建，因为 combo 触发时会用到）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._param_widget = QWidget()
        self._param_layout = QFormLayout(self._param_widget)
        self._row_widgets = {}
        self._adaptive_btns = {}
        scroll.setWidget(self._param_widget)
        layout.addWidget(scroll, 1)

        # 初始化第一级 combo
        # ROI 选择（必须在 combo 初始化前创建）
        self._roi_group = QGroupBox("选择 ROI 区域")
        self._roi_layout = QVBoxLayout(self._roi_group)
        self._roi_group.hide()
        layout.addWidget(self._roi_group)

        # 初始化第一级 combo
        self._add_combo(0, self._presets)

        # 按钮
        btn_row = QHBoxLayout()
        btn_preview = QPushButton("预览")
        btn_preview.setStyleSheet("background: #3498db; color: white; padding: 6px 16px;")
        btn_preview.clicked.connect(self._on_preview)
        btn_row.addWidget(btn_preview)

        if self._edit_mode:
            btn_update = QPushButton("更新步骤")
            btn_update.setStyleSheet("background: #e67e22; color: white; padding: 6px 16px;")
            btn_update.clicked.connect(self._on_update)
            btn_row.addWidget(btn_update)
        else:
            btn_add = QPushButton("添加到流水线")
            btn_add.setStyleSheet("background: #2ecc71; color: white; padding: 6px 16px;")
            btn_add.clicked.connect(self._on_add)
            btn_row.addWidget(btn_add)

        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet("background: #95a5a6; color: white; padding: 6px 16px;")
        btn_cancel.clicked.connect(self._on_close)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        # 编辑模式: 定位到指定函数
        if self._edit_mode and self._edit_func_name:
            self._select_func(self._edit_func_name)

    # ── 动态 combo 管理 ──
    def _add_combo(self, level: int, node: dict):
        """在指定层级添加一个 combo box。"""
        # 移除该层级及之后的所有 combo
        self._remove_combos_from(level)

        row = QHBoxLayout()
        label = QLabel(f"级别{level + 1}:" if level > 0 else "处理类别:")
        row.addWidget(label)

        combo = QComboBox()
        combo.addItems(list(node.keys()))
        row.addWidget(combo)

        # 容器 widget 用于整体移除
        container = QWidget()
        container.setLayout(row)
        self._combo_container.addWidget(container)

        self._combos.append((container, combo, node))
        combo.currentTextChanged.connect(lambda text, lv=level: self._on_combo_changed(lv, text))

        # 触发初始选中
        first_key = list(node.keys())[0] if node else None
        if first_key:
            self._on_combo_changed(level, first_key)

    def _remove_combos_from(self, level: int):
        """移除指定层级及之后的所有 combo。"""
        while len(self._combos) > level:
            container, combo, node = self._combos.pop()
            self._combo_container.removeWidget(container)
            container.deleteLater()

    def _on_combo_changed(self, level: int, text: str):
        """某个层级的 combo 选中项变化。"""
        if level >= len(self._combos):
            return

        _, _, node = self._combos[level]
        selected = node.get(text)
        if selected is None:
            return

        if _is_leaf(selected):
            # 叶子节点: 显示参数
            self._remove_combos_from(level + 1)
            self._show_params(selected)
        else:
            # 子类别: 添加下一层 combo
            self._add_combo(level + 1, selected)

    def _get_current_preset(self) -> dict:
        """获取当前选中的叶子 preset。"""
        if not self._combos:
            return {}
        # 沿 combo 链走到叶子
        node = None
        for _, combo, parent_node in self._combos:
            text = combo.currentText()
            node = parent_node.get(text)
            if node is None:
                return {}
            if _is_leaf(node):
                return node
        return {}

    def _show_params(self, preset: dict):
        """显示叶子节点的参数控件。"""
        self._current_func = preset["func"]
        self._current_params = dict(preset.get("params", {}))

        self._clear_params()
        for pname, pval in self._current_params.items():
            if pname.startswith("roi_"):
                continue
            if pname in self._param_ranges:
                self._create_widget(pname, pval)

        # 编辑模式: 覆盖值
        if self._edit_mode and self._edit_params:
            for pname, pval in self._edit_params.items():
                if pname in self._widgets:
                    w = self._widgets[pname]
                    if isinstance(w, QComboBox):
                        w.setCurrentText(str(pval))
                    elif isinstance(w, QDoubleSpinBox):
                        w.setValue(float(pval))
                    elif isinstance(w, QSpinBox):
                        w.setValue(int(pval))

        self._update_roi_checkboxes()
        self._emit_selection_changed()

    def _emit_selection_changed(self):
        """当函数或参数变化时发射信号。"""
        # 用最后一级 combo 的文本作为 display_name
        display_name = self._combos[-1][1].currentText() if self._combos else ""
        params = self._get_params()
        self.selection_changed.emit(display_name, self._current_func, params)

    def _clear_params(self):
        while self._param_layout.rowCount() > 0:
            self._param_layout.removeRow(0)
        self._widgets.clear()
        self._row_widgets.clear()
        self._adaptive_btns.clear()

    def _create_widget(self, pname, pval):
        rinfo = self._param_ranges[pname]
        label = rinfo.get("label", pname)

        if isinstance(pval, str):
            options = rinfo.get("options", [pval])
            combo = QComboBox()
            combo.addItems(options)
            combo.setCurrentText(pval)
            self._param_layout.addRow(f"{label}:", combo)
            self._widgets[pname] = combo
            self._row_widgets[pname] = combo
            combo.currentTextChanged.connect(lambda: self._emit_selection_changed())
            return

        # 判断是否是浮点数
        resolution = rinfo.get("resolution", 1)
        step = rinfo.get("step", 1)
        is_float = isinstance(pval, float) or resolution < 1
        lo, hi = rinfo["min"], rinfo["max"]

        row = QHBoxLayout()

        if is_float:
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep(resolution)
            spin.setDecimals(max(0, -int(round(__import__('math').log10(resolution), 0))) if resolution < 1 else 0)
            spin.setValue(float(pval))
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, int((hi - lo) / resolution))
            slider.setValue(int((float(pval) - lo) / resolution))

            def make_float_sync(s, sp, l, r):
                def sync(v):
                    sp.blockSignals(True)
                    sp.setValue(l + v * r)
                    sp.blockSignals(False)
                return sync

            slider.valueChanged.connect(make_float_sync(slider, spin, lo, resolution))
            spin.valueChanged.connect(lambda v: slider.setValue(int((v - lo) / resolution)))

        else:
            spin = QSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep(step)
            spin.setValue(int(pval))
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, int((hi - lo) / step))
            slider.setValue(int((int(pval) - lo) / step))

            slider.valueChanged.connect(lambda v: spin.setValue(lo + v * step))
            spin.valueChanged.connect(lambda v: slider.setValue(int((v - lo) / step)))

        spin.setFixedWidth(80)
        slider.setFixedWidth(150)

        lbl = QLabel(f"{label}:")
        lbl.setFixedWidth(80)
        row.addWidget(lbl)
        row.addWidget(slider, 1)
        row.addWidget(spin)

        # 自适应按钮 (仅 chX_max)
        if self._adaptive_callback and pname in ("ch1_max", "ch2_max", "ch3_max"):
            ch = int(pname[2])
            btn = QPushButton(self._adaptive_btn_label(ch))
            btn.setStyleSheet("background: #9b59b6; color: white; padding: 2px 8px; font-size: 10px;")
            btn.clicked.connect(lambda c=ch: self._on_adaptive(c))
            self._adaptive_btns[ch] = btn
            row.addWidget(btn)

        # K-means 按钮 (仅灰度过滤的 ch1_max)
        if (self._kmeans_callback and pname == "ch1_max"
                and self._current_params.get("color_space") == "gray"):
            btn = QPushButton("K-means 自动分割")
            btn.setStyleSheet("background: #e74c3c; color: white; padding: 2px 8px; font-size: 10px;")
            btn.clicked.connect(self._on_kmeans)
            row.addWidget(btn)

        # 用 QWidget 包装行，方便后续隐藏/显示
        row_widget = QWidget()
        row_widget.setLayout(row)
        self._param_layout.addRow(row_widget)
        self._widgets[pname] = spin
        self._row_widgets[pname] = row_widget
        spin.valueChanged.connect(lambda: self._emit_selection_changed())

    # ── ROI ──
    def _update_roi_checkboxes(self):
        while self._roi_layout.count():
            item = self._roi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._roi_regions:
            self._roi_group.hide()
            return

        self._roi_group.show()
        self._roi_vars = {}

        cb = QCheckBox("全局（不限制区域）")
        cb.setChecked(True)
        self._roi_vars["global"] = cb
        self._roi_layout.addWidget(cb)

        for roi in self._roi_regions:
            shape = "矩形" if roi["type"] == "rect" else "圆形"
            cb = QCheckBox(f"ROI #{roi['number']} ({shape})")
            cb.setStyleSheet(f"color: {roi['color']};")
            self._roi_vars[roi["number"]] = cb
            self._roi_layout.addWidget(cb)

    # ── 操作 ──
    def _get_params(self):
        params = {}
        for pname, w in self._widgets.items():
            if isinstance(w, QComboBox):
                params[pname] = w.currentText()
            elif isinstance(w, QDoubleSpinBox):
                params[pname] = w.value()
            elif isinstance(w, QSpinBox):
                params[pname] = w.value()

        if hasattr(self, '_roi_vars'):
            selected = [k for k, cb in self._roi_vars.items() if cb.isChecked()]
            params["_selected_rois"] = selected

        return params

    def _on_preview(self):
        if self._preview_callback:
            params = self._get_params()
            self._preview_callback(self._current_func, params)

    def _on_add(self):
        params = self._get_params()
        self.add_requested.emit(self._current_func, params)
        self._on_close()

    def _on_update(self):
        if self._edit_complete_callback:
            params = self._get_params()
            self._edit_complete_callback(self._current_func, params)
        self._on_close()

    def _on_close(self):
        if self._close_callback:
            self._close_callback()
            self._close_callback = None
        self.close()

    def closeEvent(self, event):
        if self._close_callback:
            self._close_callback()
            self._close_callback = None
        super().closeEvent(event)

    # ── 自适应/K-means ──
    def _adaptive_btn_label(self, ch_num: int) -> str:
        """根据当前 color_space 返回自适应按钮标签。"""
        cs = self._current_params.get("color_space", "hsv")
        ch_labels = {"hsv": ["H", "S", "V"], "rgb": ["R", "G", "B"], "gray": ["灰度", "", ""]}
        label = ch_labels.get(cs, ["1", "2", "3"])[ch_num - 1]
        return f"自适应({label})" if label else "自适应"

    def _on_kmeans(self):
        if self._kmeans_callback:
            params = self._get_params()
            result = self._kmeans_callback(self._current_func, params)
            if result:
                for pname, val in result.items():
                    if pname in self._widgets:
                        w = self._widgets[pname]
                        if isinstance(w, QDoubleSpinBox):
                            w.setValue(float(val))
                        elif isinstance(w, QSpinBox):
                            w.setValue(int(val))

    def _on_adaptive(self, channel):
        if self._adaptive_callback:
            params = self._get_params()
            result = self._adaptive_callback(self._current_func, params, channel)
            if result:
                for pname, val in result.items():
                    if pname in self._widgets:
                        w = self._widgets[pname]
                        if isinstance(w, QDoubleSpinBox):
                            w.setValue(float(val))
                        elif isinstance(w, QSpinBox):
                            w.setValue(int(val))

    def _select_func(self, func_name: str):
        """编辑模式: 根据 func_name 在树中定位，设置各级 combo。"""
        path = self._find_func_path(self._presets, func_name)
        if not path:
            return
        # 沿路径设置各级 combo
        node = self._presets
        for level, key in enumerate(path):
            if level < len(self._combos):
                _, combo, _ = self._combos[level]
                combo.setCurrentText(key)
            child = node.get(key)
            if child is None:
                break
            if _is_leaf(child):
                self._show_params(child)
                break
            else:
                if level + 1 >= len(self._combos):
                    self._add_combo(level + 1, child)
                node = child

    def _find_func_path(self, node: dict, func_name: str, path: list = None) -> list:
        """递归查找 func_name 在树中的路径。返回 [key1, key2, ...]。"""
        if path is None:
            path = []
        for key, val in node.items():
            if _is_leaf(val) and val["func"] == func_name:
                return path + [key]
            elif not _is_leaf(val) and isinstance(val, dict):
                result = self._find_func_path(val, func_name, path + [key])
                if result:
                    return result
        return []
