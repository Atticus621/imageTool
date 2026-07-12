"""PinnedParamWidget — renders pinned parameters directly on blueprint nodes.

Supports combo, checkbox, int_slider, and float_slider types.
Automatically syncs value changes back to the node's _param_values dict.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox
from PySide6.QtCore import Signal

from NodeGraphQt.widgets.node_widgets import NodeBaseWidget

# Styling is handled by custom.css — no inline setStyleSheet needed.


class PinnedComboWidget(NodeBaseWidget):
    """Embedded combo box for a pinned parameter."""

    valueChanged = Signal(str)

    def __init__(self, param_name: str, label: str, options: list, default=None, parent=None):
        super().__init__(parent, name=f"pin_{param_name}", label=" ")
        self._param_name = param_name
        self._setup_ui(label, options, default)

    def _setup_ui(self, label: str, options: list, default):
        self._combo = QComboBox()
        self._combo.setMinimumWidth(80)
        self._combo.setMinimumHeight(20)
        for opt in options:
            if isinstance(opt, dict):
                self._combo.addItem(opt.get("label", opt.get("value", "")), opt.get("value"))
            else:
                self._combo.addItem(str(opt), opt)

        # Set default
        if default is not None:
            for i in range(self._combo.count()):
                if self._combo.itemData(i) == default:
                    self._combo.setCurrentIndex(i)
                    break

        self._combo.currentIndexChanged.connect(self._on_changed)
        self.set_custom_widget(self._combo)

    def _on_changed(self, index: int):
        value = self._combo.currentData()
        self.valueChanged.emit(str(value) if value is not None else "")

    def get_value(self):
        return self._combo.currentData()

    def set_value(self, value):
        # Convert value to string for comparison (signal emits strings)
        value_str = str(value) if value is not None else ""
        for i in range(self._combo.count()):
            item_val = self._combo.itemData(i)
            if str(item_val) == value_str:
                self._combo.setCurrentIndex(i)
                break


class PinnedCheckboxWidget(NodeBaseWidget):
    """Embedded checkbox for a pinned parameter."""

    valueChanged = Signal(bool)

    def __init__(self, param_name: str, label: str, default: bool = False, parent=None):
        super().__init__(parent, name=f"pin_{param_name}", label=" ")
        self._param_name = param_name
        self._setup_ui(label, default)

    def _setup_ui(self, label: str, default: bool):
        self._checkbox = QCheckBox(label)
        self._checkbox.setChecked(default)
        self._checkbox.toggled.connect(self._on_changed)
        self.set_custom_widget(self._checkbox)

    def _on_changed(self, checked: bool):
        self.valueChanged.emit(checked)

    def get_value(self):
        return self._checkbox.isChecked()

    def set_value(self, value):
        self._checkbox.setChecked(bool(value))


class PinnedSliderWidget(NodeBaseWidget):
    """Embedded slider with spinbox for a pinned numeric parameter."""

    valueChanged = Signal(object)

    def __init__(self, param_name: str, label: str, default=None,
                 min_val=0, max_val=100, step=1, is_float=False, parent=None):
        super().__init__(parent, name=f"pin_{param_name}", label=" ")
        self._param_name = param_name
        self._is_float = is_float
        self._setup_ui(label, default, min_val, max_val, step)

    def _setup_ui(self, label, default, min_val, max_val, step):
        if self._is_float:
            self._spinbox = QDoubleSpinBox()
            self._spinbox.setDecimals(3)
            self._spinbox.setSingleStep(float(step) if step else 0.1)
            self._spinbox.setRange(float(min_val), float(max_val))
            self._spinbox.setValue(float(default) if default is not None else float(min_val))
            self._spinbox.valueChanged.connect(lambda v: self.valueChanged.emit(v))
        else:
            self._spinbox = QSpinBox()
            self._spinbox.setSingleStep(int(step) if step else 1)
            self._spinbox.setRange(int(min_val), int(max_val))
            self._spinbox.setValue(int(default) if default is not None else int(min_val))
            self._spinbox.valueChanged.connect(lambda v: self.valueChanged.emit(v))

        self._spinbox.setFixedWidth(60)
        self.set_custom_widget(self._spinbox)

    def get_value(self):
        return self._spinbox.value()

    def set_value(self, value):
        if self._is_float:
            self._spinbox.setValue(float(value))
        else:
            self._spinbox.setValue(int(value))
