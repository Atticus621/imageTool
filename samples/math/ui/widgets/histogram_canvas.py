"""Interactive histogram preview widget with per-channel toggle checkboxes."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QCheckBox
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QPolygonF
from PySide6.QtCore import Qt, Signal, QPointF, QRect

from ui.theme import BG_BASE, BORDER_DEFAULT, TEXT_PRIMARY, TEXT_MUTED, SPACING_SM, SPACING_XS


_CHANNEL_STYLESHEET = """
QCheckBox {{
    color: {color};
    font-size: 9px;
    spacing: 2px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 10px;
    height: 10px;
    border: 1px solid {color};
    border-radius: 2px;
    background: transparent;
}}
QCheckBox::indicator:checked {{
    background: {color};
}}
"""


class HistogramPreview(QWidget):
    """Interactive histogram with per-channel toggle checkboxes."""

    W = 320
    H = 170

    channel_toggled = Signal(int, bool)  # (channel_index, visible)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.setStyleSheet(f"background: {BG_BASE}; border: 1px solid {BORDER_DEFAULT};")

        self._dpr = max(self.devicePixelRatio(), 2)

        # --- stored data ---
        self._hist_data: list[list[float]] = []
        self._chan_names: list[str] = []
        self._channel_colors: list[str] = []
        self._color_space: str = ""
        self._visible: list[bool] = []
        self._checkboxes: list[QCheckBox] = []

        # --- layout ---
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        outer.setSpacing(SPACING_XS)

        # channel toggle row
        self._toggle_layout = QHBoxLayout()
        self._toggle_layout.setContentsMargins(0, 0, 0, 0)
        self._toggle_layout.setSpacing(6)
        outer.addLayout(self._toggle_layout)

        # histogram canvas
        self._label = QLabel()
        self._label.setMinimumSize(self.W - 8, self.H - 28)
        outer.addWidget(self._label, 1)

        self._draw_empty()

    # ------------------------------------------------------------------
    #  Channel toggles
    # ------------------------------------------------------------------

    def _rebuild_toggles(self):
        """Recreate checkbox row from current channel data."""
        # clear old checkboxes
        while self._toggle_layout.count():
            item = self._toggle_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._checkboxes.clear()

        for i, (name, color) in enumerate(zip(self._chan_names, self._channel_colors)):
            cb = QCheckBox(name)
            cb.setChecked(self._visible[i])
            cb.setStyleSheet(_CHANNEL_STYLESHEET.format(color=color))
            cb.stateChanged.connect(lambda state, idx=i: self._on_toggle(idx, state))
            self._toggle_layout.addWidget(cb)
            self._checkboxes.append(cb)

        self._toggle_layout.addStretch()

    def _on_toggle(self, idx: int, state: int):
        if idx < len(self._visible):
            self._visible[idx] = (state == Qt.Checked.value)
            self._redraw()
            self.channel_toggled.emit(idx, self._visible[idx])

    def set_channel_visible(self, index: int, visible: bool):
        """Programmatically show / hide a channel."""
        if 0 <= index < len(self._visible):
            self._visible[index] = visible
            if index < len(self._checkboxes):
                self._checkboxes[index].setChecked(visible)
            self._redraw()

    def get_visible_channels(self) -> list[bool]:
        return list(self._visible)

    # ------------------------------------------------------------------
    #  Data setter
    # ------------------------------------------------------------------

    def set_hist_data(
        self,
        hist_data: list[list[float]],
        chan_names: list[str],
        channel_colors: list[str],
        color_space: str,
    ):
        self._hist_data = hist_data
        self._chan_names = list(chan_names)
        self._channel_colors = list(channel_colors)
        self._color_space = color_space
        self._visible = [True] * len(hist_data)
        self._rebuild_toggles()
        self._redraw()

    # ------------------------------------------------------------------
    #  Drawing
    # ------------------------------------------------------------------

    def _make_pixmap(self) -> QPixmap:
        pw = self._label.width() or (self.W - 8)
        ph = self._label.height() or (self.H - 28)
        pm = QPixmap(pw * self._dpr, ph * self._dpr)
        pm.setDevicePixelRatio(self._dpr)
        return pm

    def _draw_empty(self):
        pm = self._make_pixmap()
        pm.fill(QColor(BG_BASE))
        p = QPainter(pm)
        p.setPen(QColor("#5a5a75"))
        font = p.font()
        font.setPointSize(9)
        p.setFont(font)
        p.drawText(pm.rect(), Qt.AlignCenter, "No Data")
        p.end()
        self._label.setPixmap(pm)

    def _redraw(self):
        if not self._hist_data:
            self._draw_empty()
            return

        pm = self._make_pixmap()
        lw = pm.width() // self._dpr
        lh = pm.height() // self._dpr
        pm.fill(QColor(BG_BASE))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)

        ml, mr, mt, mb = 36, 8, 18, 16
        pw = lw - ml - mr
        ph = lh - mt - mb

        # axes
        p.setPen(QPen(QColor(BORDER_DEFAULT), 1.5))
        p.drawLine(ml, mt, ml, mt + ph)
        p.drawLine(ml, mt + ph, ml + pw, mt + ph)

        # scale across visible channels only
        max_val = 0.0
        for vis, h in zip(self._visible, self._hist_data):
            if vis and h:
                mx = max(h)
                if mx > max_val:
                    max_val = mx
        if max_val == 0:
            max_val = 1.0

        n_bins = len(self._hist_data[0]) if self._hist_data else 1
        dx = pw / max(n_bins - 1, 1)

        # draw each visible channel
        for vis, hist, hex_c in zip(
            self._visible, self._hist_data, self._channel_colors
        ):
            if not vis:
                continue
            color = QColor(hex_c)
            fill = QColor(color)
            fill.setAlpha(80)

            pts = [QPointF(ml, mt + ph)]
            for i, v in enumerate(hist):
                x = ml + i * dx
                y = mt + ph - (v / max_val) * ph
                pts.append(QPointF(x, y))
            pts.append(QPointF(ml + pw, mt + ph))

            p.setBrush(fill)
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF(pts))

            p.setPen(QPen(color, 1.8))
            for i in range(len(pts) - 2):
                p.drawLine(pts[i + 1], pts[i + 2])

        # title & axis labels
        p.setPen(QColor(TEXT_PRIMARY))
        font = p.font()
        font.setPointSize(9)
        p.setFont(font)
        p.drawText(QRect(ml, mt - 14, pw, 14), Qt.AlignCenter,
                    f"{self._color_space.upper()}")
        p.drawText(QRect(0, mt + ph + 2, lw, 14), Qt.AlignCenter,
                    "0          128          255")

        p.end()
        self._label.setPixmap(pm)

    def clear(self):
        self._hist_data = []
        self._chan_names = []
        self._channel_colors = []
        self._visible = []
        self._checkboxes.clear()
        # clear toggle row
        while self._toggle_layout.count():
            item = self._toggle_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._draw_empty()
