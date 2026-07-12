"""FileListParamWidget — file/folder list parameter handler."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton,
)

from core.node_base.node import ParamType, ParamDefinition
from core.logger import logger
from .base import ParamWidget


class FileListParamWidget(ParamWidget):
    """File/folder list — managed list of paths with add/remove buttons.

    Accepts optional callbacks for opening file/folder dialogs (the dialog
    needs a parent window reference which lives in NodeSelectorWindow).
    """

    param_type = ParamType.FILE_LIST

    def __init__(
        self,
        param: ParamDefinition,
        *,
        add_file_callback: Callable[[], None] | None = None,
        add_folder_callback: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(param)
        self._file_items: list[QWidget] = []
        self._file_list_layout: QVBoxLayout | None = None
        self._model_info_label: QLabel | None = None
        self._add_file_callback = add_file_callback
        self._add_folder_callback = add_folder_callback

    # ── Public API for external callers ─────────────────────────────

    def add_file_item(self, path: str) -> None:
        """Append a file/folder path to the visible list."""
        if self._file_list_layout is None:
            return
        item_widget = QWidget()
        h = QHBoxLayout(item_widget)
        h.setContentsMargins(0, 2, 0, 2)
        label = QLabel(path)
        label.setWordWrap(True)
        btn_remove = QPushButton("×")  # ×
        btn_remove.setMaximumWidth(30)
        btn_remove.clicked.connect(lambda: self._remove_file_item(item_widget))
        h.addWidget(label)
        h.addWidget(btn_remove)
        self._file_list_layout.addWidget(item_widget)
        self._file_items.append(item_widget)

        if path.lower().endswith(".pt"):
            self._load_yolo_model_info(path)

    def _remove_file_item(self, widget: QWidget) -> None:
        """Remove a file item widget from the list."""
        if widget in self._file_items:
            self._file_items.remove(widget)
        widget.deleteLater()

    def _load_yolo_model_info(self, model_path: str) -> None:
        """Attempt to load a YOLO model and display its class names."""
        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
            class_names = model.names

            lines = []
            for idx, name in sorted(class_names.items()):
                lines.append(f"{idx}: {name}")
            classes_text = "\n".join(lines)

            if self._model_info_label:
                self._model_info_label.setText(
                    f"<b>可检测类别 ({len(class_names)}):</b><br>{classes_text}"
                )
                self._model_info_label.show()

            logger.info(f"YOLO model loaded: {len(class_names)} classes")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            if self._model_info_label:
                self._model_info_label.setText(f"<b>加载失败:</b> {e}")
                self._model_info_label.show()

    # ── ParamWidget interface ───────────────────────────────────────

    def create_widget(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scrollable file list
        list_container = QWidget()
        self._file_list_layout = QVBoxLayout(list_container)
        self._file_list_layout.setContentsMargins(0, 0, 0, 0)

        # Add buttons
        btn_row = QHBoxLayout()
        btn_add_file = QPushButton("+ 文件")   # + 文件
        btn_add_folder = QPushButton("+ 文件夹")  # + 文件夹
        if self._add_file_callback:
            btn_add_file.clicked.connect(self._add_file_callback)
        if self._add_folder_callback:
            btn_add_folder.clicked.connect(self._add_folder_callback)
        btn_row.addWidget(btn_add_file)
        btn_row.addWidget(btn_add_folder)
        btn_row.addStretch()

        layout.addWidget(list_container)
        layout.addLayout(btn_row)

        # Model info label (hidden by default, shown for .pt files)
        info_label = QLabel("")
        info_label.setWordWrap(True)
        info_label.hide()
        layout.addWidget(info_label)
        self._model_info_label = info_label

        self._widget = container
        return container

    def get_value(self) -> Any:
        files = []
        for item_widget in self._file_items:
            label = item_widget.findChild(QLabel)
            if label:
                files.append(label.text())
        return files

    def set_value(self, value: Any) -> None:
        if isinstance(value, list):
            for f in value:
                self.add_file_item(f)
