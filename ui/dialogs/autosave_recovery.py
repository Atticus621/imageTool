"""Auto-save recovery dialog — prompts user to recover auto-saved data."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class AutoSaveRecoveryDialog(QDialog):
    """Dialog for prompting auto-save recovery."""

    def __init__(self, project_path: Path, autosave_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("恢复自动保存")
        self.setMinimumWidth(400)
        self._project_path = project_path
        self._autosave_path = autosave_path
        self._recover = False
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Icon and message
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        title = QLabel("发现自动保存的项目文件")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # File info
        project_name = self._project_path.name
        autosave_time = datetime.fromtimestamp(self._autosave_path.stat().st_mtime)
        time_str = autosave_time.strftime("%Y-%m-%d %H:%M:%S")

        info_text = (
            f"项目文件: {project_name}\n"
            f"自动保存时间: {time_str}\n\n"
            f"是否恢复自动保存的内容？\n"
            f"（选择“不恢复”将使用原始文件）"
        )
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Buttons
        buttons = QDialogButtonBox()

        recover_btn = buttons.addButton(
            "恢复自动保存", QDialogButtonBox.ButtonRole.AcceptRole
        )
        recover_btn.setStyleSheet("background-color: #4CAF50; color: white;")

        discard_btn = buttons.addButton(
            "不恢复", QDialogButtonBox.ButtonRole.RejectRole
        )

        buttons.accepted.connect(self._on_recover)
        buttons.rejected.connect(self._on_discard)
        layout.addWidget(buttons)

    def _on_recover(self) -> None:
        self._recover = True
        self.accept()

    def _on_discard(self) -> None:
        self._recover = False
        self.accept()

    @property
    def should_recover(self) -> bool:
        """Whether the user chose to recover."""
        return self._recover
