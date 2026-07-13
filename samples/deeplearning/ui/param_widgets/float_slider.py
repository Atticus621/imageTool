"""FloatSliderParamWidget — float slider + double-spinbox parameter handler."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox

from core.node_base.node import ParamType, ParamDefinition
from .base import ParamWidget


class FloatSliderParamWidget(ParamWidget):
    """QSlider + QDoubleSpinBox — float range selection with bidirectional sync.

    Uses a multiplier of 1000 to map float values to integer slider positions.
    """

    param_type = ParamType.FLOAT_SLIDER
    MULTIPLIER = 1000

    def create_widget(self) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)

        slider = QSlider(Qt.Orientation.Horizontal)
        dspin = QDoubleSpinBox()

        mn = self.param.min_val or 0.0
        mx = self.param.max_val or 10.0
        step = self.param.step or 0.01
        default = self.param.default or 0.0

        slider.setMinimum(int(mn * self.MULTIPLIER))
        slider.setMaximum(int(mx * self.MULTIPLIER))
        slider.setSingleStep(int(step * self.MULTIPLIER))
        slider.setValue(int(default * self.MULTIPLIER))

        dspin.setMinimum(mn)
        dspin.setMaximum(mx)
        dspin.setSingleStep(step)
        dspin.setDecimals(3)
        dspin.setValue(default)

        slider.valueChanged.connect(lambda v: dspin.setValue(v / self.MULTIPLIER))
        dspin.valueChanged.connect(lambda v: slider.setValue(int(v * self.MULTIPLIER)))

        h.addWidget(slider)
        h.addWidget(dspin)
        self._widget = container
        return container

    def get_value(self) -> Any:
        dspin = self._widget.findChild(QDoubleSpinBox)
        return dspin.value() if dspin else 0.0

    def set_value(self, value: Any) -> None:
        dspin = self._widget.findChild(QDoubleSpinBox)
        if dspin:
            dspin.setValue(float(value))

    def get_value_changed_signal(self) -> Signal | None:
        dspin = self._widget.findChild(QDoubleSpinBox)
        return dspin.valueChanged if dspin else None
