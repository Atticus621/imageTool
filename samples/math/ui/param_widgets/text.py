"""TextParamWidget — single-line text input parameter handler."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLineEdit, QWidget

from core.node_base.node import ParamType, ParamDefinition
from .base import ParamWidget


class TextParamWidget(ParamWidget):
    """QLineEdit — free-form text input."""

    param_type = ParamType.TEXT

    def create_widget(self) -> QWidget:
        edit = QLineEdit()
        if self.param.default:
            edit.setText(str(self.param.default))
        self._widget = edit
        return edit

    def get_value(self) -> Any:
        return self._widget.text()

    def set_value(self, value: Any) -> None:
        self._widget.setText(str(value))
