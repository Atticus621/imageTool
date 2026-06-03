# -*- coding: utf-8 -*-
"""ROI 面板 —— ROI 列表 + 圆形扇形参数 + 矩形旋转角度编辑器。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QSlider, QDoubleSpinBox,
)


class ROIPanel(QGroupBox):
    """ROI 区域管理面板。"""

    roi_list_selection_changed = Signal(int)   # list index
    roi_sector_changed = Signal(int, str, float)  # number, key, value
    clear_rois_requested = Signal()
    roi_shape_changed = Signal(str)            # "rect" or "circle"

    def __init__(self, parent=None):
        super().__init__("ROI 区域", parent)
        self.setStyleSheet("""
            QGroupBox { font-family: 'Microsoft YaHei'; font-size: 13px; font-weight: bold;
                        background: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 4px;
                        margin-top: 8px; padding-top: 16px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        """)

        layout = QVBoxLayout(self)

        # 顶部: 计数 + 清除
        top_row = QHBoxLayout()
        self._count_label = QLabel("ROI: 0 个区域")
        self._count_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 11px;")
        top_row.addWidget(self._count_label)
        top_row.addStretch()

        btn_clear = QPushButton("清除全部")
        btn_clear.setStyleSheet(
            "background: #e74c3c; color: white; padding: 2px 8px; border: none; border-radius: 3px;")
        btn_clear.clicked.connect(lambda: self.clear_rois_requested.emit())
        top_row.addWidget(btn_clear)
        layout.addLayout(top_row)

        # ROI 列表
        self._list = QListWidget()
        self._list.setMaximumHeight(100)
        self._list.setStyleSheet("font-family: 'Consolas'; font-size: 10px;")
        self._list.currentRowChanged.connect(self.roi_list_selection_changed.emit)
        layout.addWidget(self._list)

        # 圆形扇形编辑器
        self._sector_editor = self._build_sector_editor()
        layout.addWidget(self._sector_editor)
        self._sector_editor.hide()

        # 矩形旋转编辑器
        self._rect_editor = self._build_rect_editor()
        layout.addWidget(self._rect_editor)
        self._rect_editor.hide()

        self._editing_number = None

    def _build_sector_editor(self):
        box = QGroupBox("扇形参数 (圆形ROI)")
        ly = QVBoxLayout(box)

        self._inner_ratio_slider, self._inner_ratio_spin = self._make_slider_row(
            "内圆比例:", 0.1, 0.95, 0.5, 0.05, "inner_ratio", ly)
        self._start_angle_slider, self._start_angle_spin = self._make_slider_row(
            "起始角度:", 0, 360, 0, 1, "start_angle", ly)
        self._end_angle_slider, self._end_angle_spin = self._make_slider_row(
            "终止角度:", 0, 360, 360, 1, "end_angle", ly)
        return box

    def _build_rect_editor(self):
        box = QGroupBox("旋转角度 (矩形ROI)")
        ly = QVBoxLayout(box)
        self._angle_slider, self._angle_spin = self._make_slider_row(
            "角度:", -180, 180, 0, 1, "angle", ly)
        hint = QLabel("快捷键: [ ] 键 ±5°")
        hint.setStyleSheet("color: #999; font-size: 9px;")
        ly.addWidget(hint)
        return box

    def _make_slider_row(self, label_text, lo, hi, default, step, key, layout):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(60)
        lbl.setStyleSheet("font-size: 10px;")
        row.addWidget(lbl)

        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setSingleStep(step)
        spin.setValue(default)
        spin.setDecimals(2 if step < 1 else 0)
        spin.setFixedWidth(70)
        spin.setStyleSheet("font-family: 'Consolas'; font-size: 10px;")

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, int((hi - lo) / step))
        slider.setValue(int((default - lo) / step))

        # 同步 slider ↔ spin
        def spin_changed(v):
            slider.blockSignals(True)
            slider.setValue(int((v - lo) / step))
            slider.blockSignals(False)
            self._emit_param(key, v)

        def slider_changed(v):
            val = lo + v * step
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)
            self._emit_param(key, val)

        spin.valueChanged.connect(spin_changed)
        slider.valueChanged.connect(slider_changed)

        row.addWidget(slider)
        row.addWidget(spin)
        layout.addLayout(row)
        return slider, spin

    def _emit_param(self, key: str, value: float):
        if self._editing_number is not None:
            self.roi_sector_changed.emit(self._editing_number, key, value)

    # ── 公共 ──
    def update_display(self, regions: list):
        self._list.blockSignals(True)
        self._list.clear()
        for roi in regions:
            shape = "矩形" if roi["type"] == "rect" else "圆形"
            text = f"#{roi['number']} {shape} {roi['coords']}"
            if roi["type"] == "rect":
                a = roi.get("angle", 0.0)
                if abs(a) >= 0.01:
                    text += f"  ∠{a:.0f}°"
            item = QListWidgetItem(text)
            item.setForeground(QColor(roi["color"]))
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._count_label.setText(f"ROI: {len(regions)} 个区域")

    def show_editor(self, roi: dict):
        if roi is None:
            self._sector_editor.hide()
            self._rect_editor.hide()
            self._editing_number = None
            return

        self._editing_number = roi["number"]

        if roi["type"] == "circle":
            self._rect_editor.hide()
            self._set_slider(self._inner_ratio_spin, self._inner_ratio_slider,
                             0.1, 0.05, roi.get("inner_ratio", 0.5))
            self._set_slider(self._start_angle_spin, self._start_angle_slider,
                             0, 1, roi.get("start_angle", 0.0))
            self._set_slider(self._end_angle_spin, self._end_angle_slider,
                             0, 1, roi.get("end_angle", 360.0))
            self._sector_editor.show()
        elif roi["type"] == "rect":
            self._sector_editor.hide()
            self._set_slider(self._angle_spin, self._angle_slider,
                             -180, 1, roi.get("angle", 0.0))
            self._rect_editor.show()

    def hide_editor(self):
        self._sector_editor.hide()
        self._rect_editor.hide()
        self._editing_number = None

    def update_angle(self, value: float):
        """拖拽旋转时更新角度显示。"""
        if self._editing_number is not None:
            self._angle_spin.blockSignals(True)
            self._angle_spin.setValue(value)
            self._angle_spin.blockSignals(False)
            self._angle_slider.blockSignals(True)
            self._angle_slider.setValue(int((value + 180)))
            self._angle_slider.blockSignals(False)

    def _set_slider(self, spin, slider, lo, step, val):
        spin.blockSignals(True)
        spin.setValue(val)
        spin.blockSignals(False)
        slider.blockSignals(True)
        slider.setValue(int((val - lo) / step))
        slider.blockSignals(False)

    def selected_index(self):
        return self._list.currentRow()

    def select_row(self, idx: int):
        """编程选中指定行。"""
        self._list.blockSignals(True)
        self._list.setCurrentRow(idx)
        self._list.blockSignals(False)
