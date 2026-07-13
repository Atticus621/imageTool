"""Template selection dialog — allows users to choose a template."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.project import TemplateInfo


class TemplateDialog(QDialog):
    """Dialog for selecting a project template."""

    template_selected = Signal(str)  # Emits template ID

    def __init__(self, templates: list[TemplateInfo], parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择项目模板")
        self.setMinimumSize(500, 400)
        self._templates = {t.id: t for t in templates}
        self._selected_id: str | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Template list
        list_label = QLabel("可用模板:")
        layout.addWidget(list_label)

        self._list_widget = QListWidget()
        self._list_widget.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list_widget)

        # Description area
        self._desc_label = QLabel("描述:")
        layout.addWidget(self._desc_label)

        self._desc_text = QTextEdit()
        self._desc_text.setReadOnly(True)
        self._desc_text.setMaximumHeight(80)
        layout.addWidget(self._desc_text)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        # Add empty project button
        self._empty_btn = QPushButton("空白项目")
        self._empty_btn.clicked.connect(self._on_empty_project)
        buttons.addButton(self._empty_btn, QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(buttons)

        # Populate list
        self._populate_list()

    def _populate_list(self) -> None:
        """Populate the template list."""
        # Add empty project option
        item = QListWidgetItem("空白项目")
        item.setData(Qt.ItemDataRole.UserRole, "")
        self._list_widget.addItem(item)

        # Add templates
        for template in self._templates.values():
            prefix = "[内置] " if template.is_builtin else "[用户] "
            item = QListWidgetItem(f"{prefix}{template.name}")
            item.setData(Qt.ItemDataRole.UserRole, template.id)
            self._list_widget.addItem(item)

        # Select first item
        if self._list_widget.count() > 0:
            self._list_widget.setCurrentRow(0)

    def _on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle template selection change."""
        if current is None:
            self._desc_text.clear()
            return

        template_id = current.data(Qt.ItemDataRole.UserRole)
        if not template_id:
            self._desc_text.setText("创建一个空白项目")
            return

        template = self._templates.get(template_id)
        if template:
            desc = template.description or "无描述"
            author = f"\n作者: {template.author}" if template.author else ""
            self._desc_text.setText(f"{desc}{author}")

    def _on_accept(self) -> None:
        """Handle OK button click."""
        current = self._list_widget.currentItem()
        if current:
            self._selected_id = current.data(Qt.ItemDataRole.UserRole)
            self.template_selected.emit(self._selected_id or "")
        self.accept()

    def _on_empty_project(self) -> None:
        """Handle empty project button click."""
        self._selected_id = ""
        self.template_selected.emit("")
        self.accept()

    @property
    def selected_template_id(self) -> str | None:
        """Get the selected template ID."""
        return self._selected_id
