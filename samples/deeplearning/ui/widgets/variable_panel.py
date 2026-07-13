"""Variable panel widget — displays and edits global variables."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QLineEdit, QDoubleSpinBox,
    QCheckBox, QGroupBox,
)

from core.logger import logger
from core.variable import variable_registry, Variable, VariableType
from ui.theme import TEXT_PRIMARY, FONT_SIZE_LG


class VariablePanel(QWidget):
    """Panel for viewing and editing global variables."""

    variable_changed = Signal(str, object)  # name, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._refresh_table()

        # Listen for variable changes
        variable_registry.on_changed.connect(self._on_variable_changed)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Header
        header = QLabel("全局变量")
        header.setStyleSheet(f"font-weight: bold; font-size: {FONT_SIZE_LG}; color: {TEXT_PRIMARY};")
        layout.addWidget(header)

        # Add variable controls
        add_layout = QHBoxLayout()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("变量名")
        self._name_edit.setMaximumWidth(120)
        add_layout.addWidget(self._name_edit)

        self._type_combo = QComboBox()
        self._type_combo.addItems(["number", "string", "bool", "list"])
        self._type_combo.setMaximumWidth(80)
        add_layout.addWidget(self._type_combo)

        self._value_edit = QLineEdit()
        self._value_edit.setPlaceholderText("值")
        add_layout.addWidget(self._value_edit, 1)

        btn_add = QPushButton("+ 添加")
        btn_add.clicked.connect(self._add_variable)
        add_layout.addWidget(btn_add)

        layout.addLayout(add_layout)

        # Variable table
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["名称", "类型", "值"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_delete = QPushButton("删除选中")
        btn_delete.clicked.connect(self._delete_selected)
        btn_clear = QPushButton("清空全部")
        btn_clear.clicked.connect(self._clear_all)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_clear)
        layout.addLayout(btn_layout)

    def _add_variable(self):
        """Add a new variable."""
        name = self._name_edit.text().strip()
        if not name:
            return

        type_str = self._type_combo.currentText()
        value_str = self._value_edit.text().strip()

        # Parse value based on type
        try:
            if type_str == "number":
                value = float(value_str) if value_str else 0.0
            elif type_str == "bool":
                value = value_str.lower() in ("true", "1", "yes")
            elif type_str == "list":
                value = [v.strip() for v in value_str.split(",") if v.strip()]
            else:
                value = value_str
        except ValueError:
            value = value_str

        from core.variable import VariableType
        var_type = VariableType(type_str)
        variable_registry.set(name, value, var_type)

        # Clear inputs
        self._name_edit.clear()
        self._value_edit.clear()
        self._refresh_table()

    def _delete_selected(self):
        """Delete selected variable."""
        row = self._table.currentRow()
        if row >= 0:
            name = self._table.item(row, 0).text()
            variable_registry.delete(name)
            self._refresh_table()

    def _clear_all(self):
        """Clear all variables."""
        variable_registry.clear()
        self._refresh_table()

    def _refresh_table(self):
        """Refresh the variable table."""
        variables = variable_registry.list()
        self._table.setRowCount(len(variables))

        for i, var in enumerate(variables):
            self._table.setItem(i, 0, QTableWidgetItem(var.name))
            self._table.setItem(i, 1, QTableWidgetItem(var.var_type.value))
            self._table.setItem(i, 2, QTableWidgetItem(str(var.value)))

    def _on_variable_changed(self, name: str, value):
        """Handle variable change from registry."""
        self._refresh_table()
        self.variable_changed.emit(name, value)
