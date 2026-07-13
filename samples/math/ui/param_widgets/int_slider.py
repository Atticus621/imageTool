"""IntSliderParamWidget — integer slider + spinbox parameter handler."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QSpinBox

from core.node_base.node import ParamType, ParamDefinition
from .base import ParamWidget


class IntSliderParamWidget(ParamWidget):
    """QSlider + QSpinBox — integer range selection with bidirectional sync."""

    param_type = ParamType.INT_SLIDER

    def create_widget(self) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)

        slider = QSlider(Qt.Orientation.Horizontal)
        spin = QSpinBox()

        mn = self.param.min_val or 0
        mx = self.param.max_val or 100
        step = self.param.step or 1
        default = self.param.default or 0

        slider.setMinimum(mn)
        slider.setMaximum(mx)
        slider.setSingleStep(step)
        slider.setValue(default)
        spin.setMinimum(mn)
        spin.setMaximum(mx)
        spin.setSingleStep(step)
        spin.setValue(default)

        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)

        h.addWidget(slider)
        h.addWidget(spin)
        self._widget = container
        return container

    def get_value(self) -> Any:
        spin = self._widget.findChild(QSpinBox)
        return spin.value() if spin else 0

    def set_value(self, value: Any) -> None:
        spin = self._widget.findChild(QSpinBox)
        if spin:
            spin.setValue(int(value))

    def get_value_changed_signal(self) -> Signal | None:
        spin = self._widget.findChild(QSpinBox)
        return spin.valueChanged if spin else None
