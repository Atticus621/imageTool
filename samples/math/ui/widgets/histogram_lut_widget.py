"""HistogramLUTWidget — interactive histogram with LUT range control."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel
from PySide6.QtCore import Qt, Signal

from ui.widgets.range_slider import RangeSlider
from ui.widgets.histogram_canvas import HistogramPreview
from ui.theme import SPACING_SM, SPACING_XS


class HistogramLUTWidget(QWidget):
    """Histogram display with LUT range slider for brightness/contrast control."""

    rangeChanged = Signal(int, int)  # (lower, upper)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        layout.setSpacing(SPACING_SM)

        # Histogram preview
        self._histogram = HistogramPreview()
        layout.addWidget(self._histogram, 1)

        # LUT range slider
        self._range_slider = RangeSlider()
        self._range_slider.setMinimum(0)
        self._range_slider.setMaximum(255)
        self._range_slider.setLower(0)
        self._range_slider.setUpper(255)
        self._range_slider.rangeChanged.connect(self._on_range_changed)
        layout.addWidget(self._range_slider)

        # Range labels
        labels_layout = QHBoxLayout()
        self._lower_label = QLabel("0")
        self._upper_label = QLabel("255")
        labels_layout.addWidget(self._lower_label)
        labels_layout.addStretch()
        labels_layout.addWidget(self._upper_label)
        layout.addLayout(labels_layout)

    def _on_range_changed(self, lower: int, upper: int):
        self._lower_label.setText(str(lower))
        self._upper_label.setText(str(upper))
        self.rangeChanged.emit(lower, upper)

    def set_hist_data(self, hist_data, chan_names, channel_colors, color_space):
        """Update histogram data."""
        self._histogram.set_hist_data(hist_data, chan_names, channel_colors, color_space)

    def set_channel_visible(self, index: int, visible: bool):
        """Show/hide a specific channel."""
        self._histogram.set_channel_visible(index, visible)

    def get_visible_channels(self) -> list[bool]:
        """Get visibility state of all channels."""
        return self._histogram.get_visible_channels()

    def get_lut_range(self) -> tuple[int, int]:
        """Get current LUT range (lower, upper)."""
        return self._range_slider.get_lower(), self._range_slider.get_upper()

    def set_lut_range(self, lower: int, upper: int):
        """Set LUT range."""
        self._range_slider.setLower(lower)
        self._range_slider.setUpper(upper)

    def clear(self):
        """Clear histogram data."""
        self._histogram.clear()
        self._range_slider.setLower(0)
        self._range_slider.setUpper(255)