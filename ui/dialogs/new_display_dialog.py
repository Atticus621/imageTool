"""NewDisplayDialog — dialog for creating or selecting a custom display."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QButtonGroup, QRadioButton, QWidget,
)


class NewDisplayDialog(QDialog):
    """Dialog for creating a new display or selecting an existing one.

    Modes:
    - create: User enters a name for a new display
    - select: User picks an existing display from a list
    """

    def __init__(self, existing_displays: dict[str, str], parent=None):
        """
        Args:
            existing_displays: {display_id: display_name} of existing displays.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._existing_displays = existing_displays
        self._selected_display_id: str | None = None
        self._new_display_name: str = ""
        self._mode = "select" if existing_displays else "create"

        self.setWindowTitle("添加到显示")
        self.setMinimumWidth(320)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        if self._existing_displays:
            # Mode: select existing or create new
            self._select_radio = QRadioButton("选择已有显示")
            self._create_radio = QRadioButton("新建显示")
            self._select_radio.setChecked(True)

            self._button_group = QButtonGroup(self)
            self._button_group.addButton(self._select_radio, 0)
            self._button_group.addButton(self._create_radio, 1)

            layout.addWidget(self._select_radio)

            # Existing display selector
            self._display_combo = QComboBox()
            for did, dname in self._existing_displays.items():
                self._display_combo.addItem(dname, did)
            layout.addWidget(self._display_combo)

            layout.addWidget(self._create_radio)

            # New display name input
            self._name_input = QLineEdit()
            self._name_input.setPlaceholderText("输入显示名称...")
            self._name_input.setEnabled(False)
            layout.addWidget(self._name_input)

            # Connect radio buttons
            self._select_radio.toggled.connect(self._on_mode_changed)
            self._create_radio.toggled.connect(self._on_mode_changed)
        else:
            # Mode: create only
            layout.addWidget(QLabel("输入新显示的名称:"))
            self._name_input = QLineEdit()
            self._name_input.setPlaceholderText("显示名称...")
            layout.addWidget(self._name_input)

        # Error label
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #ff6b6b;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._ok_btn = QPushButton("确定")
        self._ok_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(self._ok_btn)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

    def _on_mode_changed(self):
        is_select = self._select_radio.isChecked()
        self._display_combo.setEnabled(is_select)
        self._name_input.setEnabled(not is_select)
        self._error_label.hide()

    def _on_accept(self):
        if hasattr(self, '_select_radio') and self._select_radio.isChecked():
            # Select existing
            idx = self._display_combo.currentIndex()
            if idx >= 0:
                self._selected_display_id = self._display_combo.itemData(idx)
                self.accept()
        else:
            # Create new
            name = self._name_input.text().strip()
            if not name:
                self._error_label.setText("请输入显示名称")
                self._error_label.show()
                return

            # Check for duplicate names
            for did, dname in self._existing_displays.items():
                if dname == name:
                    self._error_label.setText("显示名称已存在")
                    self._error_label.show()
                    return

            self._new_display_name = name
            self._selected_display_id = None
            self.accept()

    @property
    def selected_display_id(self) -> str | None:
        """The selected existing display ID (or None if creating new)."""
        return self._selected_display_id

    @property
    def new_display_name(self) -> str:
        """The new display name (empty if selecting existing)."""
        return self._new_display_name

    @property
    def is_create_mode(self) -> bool:
        """Whether the user chose to create a new display."""
        return self._selected_display_id is None
