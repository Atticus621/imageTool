"""ChannelRangeParamWidget — dual-handle range slider with per-channel labels."""

from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpinBox

from core.node_base.node import ParamType, ParamDefinition
from ui.widgets.range_slider import RangeSlider
from .base import ParamWidget


class ChannelRangeParamWidget(ParamWidget):
    """Dual-handle RangeSlider + two QSpinBoxes for one channel's [lower, upper] range.

    The channel label text and slider range are updated dynamically via
    ``on_dependency_change`` when the ``channel_type`` combo changes.
    """

    param_type = ParamType.CHANNEL_RANGE

    def create_widget(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Channel name label (text updated dynamically)
        chan_label = QLabel(self.param.label or self.param.name)
        chan_label.setMinimumWidth(24)
        chan_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(chan_label)

        # Range slider
        slider = RangeSlider()
        slider.setMinimum(self.param.min_val or 0)
        slider.setMaximum(self.param.max_val or 255)
        slider.setStep(self.param.step or 1)
        if isinstance(self.param.default, list) and len(self.param.default) >= 2:
            slider.setRange(int(self.param.default[0]), int(self.param.default[1]))
        else:
            slider.setRange(self.param.min_val or 0, self.param.max_val or 255)
        layout.addWidget(slider, 1)  # stretch

        # Lower spinbox
        lower_spin = QSpinBox()
        lower_spin.setMinimum(self.param.min_val or 0)
        lower_spin.setMaximum(self.param.max_val or 255)
        lower_spin.setSingleStep(self.param.step or 1)
        lower_spin.setValue(slider.lower)
        lower_spin.setMaximumWidth(60)
        layout.addWidget(lower_spin)

        # Upper spinbox
        upper_spin = QSpinBox()
        upper_spin.setMinimum(self.param.min_val or 0)
        upper_spin.setMaximum(self.param.max_val or 255)
        upper_spin.setSingleStep(self.param.step or 1)
        upper_spin.setValue(slider.upper)
        upper_spin.setMaximumWidth(60)
        layout.addWidget(upper_spin)

        # Bidirectional connections
        slider.lowerChanged.connect(lower_spin.setValue)
        lower_spin.valueChanged.connect(slider.setLower)
        slider.upperChanged.connect(upper_spin.setValue)
        upper_spin.valueChanged.connect(slider.setUpper)

        self._widget = container
        return container

    # ── ParamWidget interface ───────────────────────────────────────

    def get_value(self) -> Any:
        slider = self._widget.findChild(RangeSlider)
        if slider:
            return [slider.lower, slider.upper]
        return [0, 0]

    def set_value(self, value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2:
            slider = self._widget.findChild(RangeSlider)
            if slider:
                slider.setRange(int(value[0]), int(value[1]))

    def needs_own_label(self) -> bool:
        return True

    # ── Dependency hook ─────────────────────────────────────────────

    def on_dependency_change(self, source_name: str, source_value: Any) -> bool:
        """Handle channel_type changes: update label, range, visibility."""
        from core.image_data import CHANNEL_NAMES, CHANNEL_RANGES, ColorSpace

        try:
            cs_enum = ColorSpace(source_value)
        except (ValueError, KeyError):
            self._widget.setVisible(False)
            return True

        names = CHANNEL_NAMES.get(cs_enum, ())
        ranges = CHANNEL_RANGES.get(cs_enum, [(0, 255)])
        num_channels = len(ranges)

        idx = self._channel_index()
        if idx is None or idx >= num_channels:
            self._widget.setVisible(False)
            return True

        self._widget.setVisible(True)
        chan_name = names[idx] if idx < len(names) else f"Ch{idx + 1}"
        chan_min, chan_max = ranges[idx]

        # Update label
        label = self._widget.findChild(QLabel)
        if label:
            label.setText(chan_name)

        # Update slider
        slider = self._widget.findChild(RangeSlider)
        if slider:
            slider.setMinimum(chan_min)
            slider.setMaximum(chan_max)
            slider.setLower(max(chan_min, min(chan_max, slider.lower)))
            slider.setUpper(max(chan_min, min(chan_max, slider.upper)))

        # Update spinbox ranges
        for spin in self._widget.findChildren(QSpinBox):
            spin.setMinimum(chan_min)
            spin.setMaximum(chan_max)

        return True

    def _channel_index(self) -> int | None:
        """Extract the channel index from the param name, e.g. 'channel_0' -> 0."""
        m = re.search(r"channel_(\d+)", self.param.name)
        return int(m.group(1)) if m else None
