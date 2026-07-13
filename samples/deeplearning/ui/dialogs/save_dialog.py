"""Save project dialog — collects project metadata before saving."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SaveDialog(QDialog):
    """Dialog for saving project with metadata."""

    def __init__(self, parent=None, project_name: str = "", description: str = ""):
        super().__init__(parent)
        self.setWindowTitle("保存项目")
        self.setMinimumWidth(400)
        self._init_ui(project_name, description)

    def _init_ui(self, project_name: str, description: str) -> None:
        layout = QVBoxLayout(self)

        # Form layout
        form = QFormLayout()

        self._name_edit = QLineEdit(project_name)
        self._name_edit.setPlaceholderText("项目名称")
        form.addRow("项目名称:", self._name_edit)

        self._desc_edit = QTextEdit(description)
        self._desc_edit.setPlaceholderText("项目描述（可选）")
        self._desc_edit.setMaximumHeight(100)
        form.addRow("描述:", self._desc_edit)

        self._author_edit = QLineEdit()
        self._author_edit.setPlaceholderText("作者（可选）")
        form.addRow("作者:", self._author_edit)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("标签，用逗号分隔（可选）")
        form.addRow("标签:", self._tags_edit)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def project_name(self) -> str:
        return self._name_edit.text().strip()

    @property
    def description(self) -> str:
        return self._desc_edit.toPlainText().strip()

    @property
    def author(self) -> str:
        return self._author_edit.text().strip()

    @property
    def tags(self) -> list[str]:
        text = self._tags_edit.text().strip()
        if not text:
            return []
        return [t.strip() for t in text.split(",") if t.strip()]
