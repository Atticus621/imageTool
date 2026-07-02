"""ComboParamWidget — dropdown (QComboBox) parameter handler."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QWidget

from core.node_base.node import ParamType, ParamDefinition
from .base import ParamWidget


class ComboParamWidget(ParamWidget):
    """QComboBox — selection from a fixed list of options."""

    param_type = ParamType.COMBO

    def create_widget(self) -> QWidget:
        combo = QComboBox()
        for opt in self.param.options:
            combo.addItem(opt.label, opt.value)
        if self.param.default is not None:
            idx = combo.findData(self.param.default)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        self._widget = combo
        return combo

    def get_value(self) -> Any:
        return self._widget.currentData()

    def set_value(self, value: Any) -> None:
        idx = self._widget.findData(value)
        if idx >= 0:
            self._widget.setCurrentIndex(idx)

    def get_value_changed_signal(self) -> Signal | None:
        return self._widget.currentIndexChanged

    def on_dependency_change(self, source_name: str, source_value: Any) -> bool:
        # Combo options can be repopulated here if needed.
        return False
