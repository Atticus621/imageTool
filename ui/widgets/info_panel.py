"""Image info panel — displays pixel-level image information.

UI component with zero business logic — receives PixelInfo objects
and renders them. ImageInfoSystem owns all computation.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
)


class InfoPanelWidget(QFrame):
    """Embedded panel showing pixel coordinates, color values, and image size.

    Receives PixelInfo via update_info() — no computation, pure display.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMaximumHeight(36)
        self._init_ui()
        self._show_placeholder()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        # Position
        self._pos_label = QLabel()
        self._pos_label.setStyleSheet("font-size: 10px; color: #aaa;")
        layout.addWidget(self._pos_label)

        # Image size
        self._size_label = QLabel()
        self._size_label.setStyleSheet("font-size: 10px; color: #aaa;")
        layout.addWidget(self._size_label)

        # Channel values
        self._channels_label = QLabel()
        self._channels_label.setStyleSheet("font-size: 10px; color: #0ff;")
        self._channels_label.setWordWrap(False)
        layout.addWidget(self._channels_label, 1)

    def update_info(self, pixel_info) -> None:
        """Update the display with new pixel information.

        Args:
            pixel_info: PixelInfo instance, or None to show placeholder.
        """
        if pixel_info is None:
            self._show_placeholder()
            return

        self._pos_label.setText(f"位置: {pixel_info.position_str}")
        self._size_label.setText(f"尺寸: {pixel_info.size_str}")
        self._channels_label.setText(f"通道: {pixel_info.channels_str}")

    def _show_placeholder(self):
        self._pos_label.setText("位置: —")
        self._size_label.setText("尺寸: —")
        self._channels_label.setText("通道: 将鼠标移到图像上查看")
