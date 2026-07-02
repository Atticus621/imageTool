"""CheckboxParamWidget — boolean checkbox parameter handler."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QCheckBox, QWidget

from core.node_base.node import ParamType, ParamDefinition
from .base import ParamWidget


class CheckboxParamWidget(ParamWidget):
    """QCheckBox — boolean toggle."""

    param_type = ParamType.CHECKBOX

    def create_widget(self) -> QWidget:
        cb = QCheckBox()
        cb.setChecked(bool(self.param.default))
        self._widget = cb
        return cb

    def get_value(self) -> Any:
        return self._widget.isChecked()

    def set_value(self, value: Any) -> None:
        self._widget.setChecked(bool(value))
