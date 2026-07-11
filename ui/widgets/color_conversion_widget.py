"""Color conversion widget for embedding in NodeGraphQt nodes."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
from PySide6.QtCore import Signal

from NodeGraphQt.widgets.node_widgets import NodeBaseWidget


class ColorConversionWidget(NodeBaseWidget):
    """Embedded widget for color conversion node with target color space selection."""

    colorSpaceChanged = Signal(str)  # emits new target color space

    # Color space options matching meta.json
    COLOR_SPACES = [
        ("bgr", "BGR (OpenCV 默认)"),
        ("rgb", "RGB"),
        ("hsv", "HSV"),
        ("hls", "HLS"),
        ("lab", "LAB"),
        ("luv", "LUV"),
        ("gray", "GRAY (灰度)"),
        ("xyz", "XYZ"),
        ("ycr_cb", "YCrCb"),
    ]

    def __init__(self, parent=None, name="color_conversion", label=" "):
        super().__init__(parent, name=name, label=label)
        self._setup_ui()

    def _setup_ui(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        label = QLabel("目标色彩空间:")
        label.setStyleSheet("color: #cccccc; font-size: 10px;")
        layout.addWidget(label)

        self._combo = QComboBox()
        for value, text in self.COLOR_SPACES:
            self._combo.addItem(text, value)
        self._combo.setStyleSheet("""
            QComboBox {
                background: #2b2b3d;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 10px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #2b2b3d;
                color: #cccccc;
                selection-background-color: #3b3b4d;
            }
        """)
        self._combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self._combo, 1)

        self.set_custom_widget(container)

    def _on_selection_changed(self, index: int):
        value = self._combo.itemData(index)
        self.colorSpaceChanged.emit(value)
        # Update the node's param value if we have access to it
        # This will be handled by the main window connection

    def get_value(self) -> str:
        """Return current selected color space value."""
        return self._combo.currentData()

    def set_value(self, value: str):
        """Set combo box to the given color space value."""
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == value:
                self._combo.setCurrentIndex(i)
                break

    def set_color_spaces(self, spaces: list[tuple[str, str]]):
        """Update available color spaces."""
        current = self.get_value()
        self._combo.clear()
        for value, text in spaces:
            self._combo.addItem(text, value)
        # Try to restore previous selection
        self.set_value(current)