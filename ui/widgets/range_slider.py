"""RangeSlider — dual-handle slider for selecting a [lower, upper] range."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QBrush
from PySide6.QtWidgets import QWidget


class RangeSlider(QWidget):
    """A horizontal slider with two draggable handles for range selection.

    Signals:
        lowerChanged(int): emitted when the lower handle value changes.
        upperChanged(int): emitted when the upper handle value changes.
        rangeChanged(int, int): emitted when either handle value changes.
    """

    lowerChanged = Signal(int)
    upperChanged = Signal(int)
    rangeChanged = Signal(int, int)

    # ── Visual constants ──────────────────────────────────────────────
    TRACK_HEIGHT = 6
    HANDLE_WIDTH = 10
    HANDLE_HEIGHT = 22
    HANDLE_RADIUS = 3
    TRACK_RADIUS = 3
    HIT_MARGIN = 12  # extra px on each side of handle for mouse hit detection

    COLOR_TRACK = QColor(70, 70, 80)
    COLOR_RANGE = QColor(0, 150, 200)
    COLOR_HANDLE = QColor(0, 180, 230)
    COLOR_HANDLE_HOVER = QColor(60, 210, 255)
    COLOR_HANDLE_DRAG = QColor(100, 230, 255)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._minimum = 0
        self._maximum = 255
        self._step = 1
        self._lower = 0
        self._upper = 255
        self._dragging: str | None = None  # 'lower' | 'upper' | None
        self._hover_handle: str | None = None  # 'lower' | 'upper' | None
        self._drag_anchor_value = 0  # value at mouse press, for consistent drag

        self.setMinimumHeight(36)
        self.setMouseTracking(True)

    # ── Public properties ──────────────────────────────────────────────
    @property
    def minimum(self) -> int:
        return self._minimum

    def setMinimum(self, val: int):
        val = int(val)
        if val != self._minimum:
            self._minimum = val
            # Clamp values
            if self._lower < self._minimum:
                self.setLower(self._minimum)
            if self._upper < self._minimum:
                self.setUpper(self._minimum)
            if self._maximum < self._minimum:
                self._maximum = self._minimum
            self.update()

    @property
    def maximum(self) -> int:
        return self._maximum

    def setMaximum(self, val: int):
        val = int(val)
        if val != self._maximum:
            self._maximum = val
            if self._upper > self._maximum:
                self.setUpper(self._maximum)
            if self._lower > self._maximum:
                self.setLower(self._maximum)
            if self._minimum > self._maximum:
                self._minimum = self._maximum
            self.update()

    @property
    def step(self) -> int:
        return self._step

    def setStep(self, val: int):
        self._step = max(1, int(val))

    @property
    def lower(self) -> int:
        return self._lower

    def setLower(self, val: int):
        val = self._snap(int(val))
        val = max(self._minimum, min(self._maximum, val))
        if val > self._upper:
            self._upper = val
            self.upperChanged.emit(self._upper)
        if val != self._lower:
            self._lower = val
            self.lowerChanged.emit(self._lower)
            self.rangeChanged.emit(self._lower, self._upper)
            self.update()

    @property
    def upper(self) -> int:
        return self._upper

    def setUpper(self, val: int):
        val = self._snap(int(val))
        val = max(self._minimum, min(self._maximum, val))
        if val < self._lower:
            self._lower = val
            self.lowerChanged.emit(self._lower)
        if val != self._upper:
            self._upper = val
            self.upperChanged.emit(self._upper)
            self.rangeChanged.emit(self._lower, self._upper)
            self.update()

    def setRange(self, lower: int, upper: int):
        """Set both handle values at once (emits signals once each if changed)."""
        lower = self._snap(max(self._minimum, min(self._maximum, int(lower))))
        upper = self._snap(max(self._minimum, min(self._maximum, int(upper))))
        if lower > upper:
            lower, upper = upper, lower
        changed = False
        if lower != self._lower:
            self._lower = lower
            self.lowerChanged.emit(self._lower)
            changed = True
        if upper != self._upper:
            self._upper = upper
            self.upperChanged.emit(self._upper)
            changed = True
        if changed:
            self.rangeChanged.emit(self._lower, self._upper)
            self.update()

    # ── Internal helpers ───────────────────────────────────────────────
    def _track_rect(self) -> QRectF:
        """Rectangle of the slider track in widget coordinates."""
        margin_x = self.HANDLE_WIDTH // 2 + 2
        y = (self.height() - self.TRACK_HEIGHT) / 2.0
        return QRectF(
            float(margin_x),
            y,
            float(self.width() - 2 * margin_x),
            float(self.TRACK_HEIGHT),
        )

    def _value_to_x(self, value: int) -> float:
        """Map a value to an x pixel position on the track."""
        tr = self._track_rect()
        span = self._maximum - self._minimum
        if span == 0:
            return tr.left()
        ratio = (value - self._minimum) / span
        return tr.left() + ratio * tr.width()

    def _x_to_value(self, x: float) -> int:
        """Map an x pixel position to a snapped value."""
        tr = self._track_rect()
        ratio = max(0.0, min(1.0, (x - tr.left()) / tr.width()))
        raw = self._minimum + ratio * (self._maximum - self._minimum)
        return self._snap(round(raw))

    def _snap(self, value: int) -> int:
        """Snap value to the nearest step."""
        if self._step <= 0:
            return value
        return round(value / self._step) * self._step

    def _handle_rect(self, which: str) -> QRectF:
        """Rectangle of a handle in widget coordinates."""
        tr = self._track_rect()
        x = self._value_to_x(self._lower if which == "lower" else self._upper)
        return QRectF(
            x - self.HANDLE_WIDTH / 2.0,
            (self.height() - self.HANDLE_HEIGHT) / 2.0,
            float(self.HANDLE_WIDTH),
            float(self.HANDLE_HEIGHT),
        )

    def _hit_handle(self, pos_x: float) -> str | None:
        """Return 'lower', 'upper', or None based on which handle is near pos_x."""
        lower_x = self._value_to_x(self._lower)
        upper_x = self._value_to_x(self._upper)
        dist_lower = abs(pos_x - lower_x)
        dist_upper = abs(pos_x - upper_x)
        hit_dist = self.HANDLE_WIDTH / 2.0 + self.HIT_MARGIN

        near_lower = dist_lower < hit_dist
        near_upper = dist_upper < hit_dist

        if near_lower and near_upper:
            return "lower" if dist_lower <= dist_upper else "upper"
        if near_lower:
            return "lower"
        if near_upper:
            return "upper"
        return None

    # ── Paint ───────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        tr = self._track_rect()

        # ── Track background ────────────────────────────────────────
        track_path = QPainterPath()
        track_path.addRoundedRect(tr, self.TRACK_RADIUS, self.TRACK_RADIUS)
        painter.fillPath(track_path, QBrush(self.COLOR_TRACK))

        # ── Highlighted range ───────────────────────────────────────
        lower_x = self._value_to_x(self._lower)
        upper_x = self._value_to_x(self._upper)
        if upper_x > lower_x:
            range_rect = QRectF(lower_x, tr.top(), upper_x - lower_x, tr.height())
            range_path = QPainterPath()
            range_path.addRoundedRect(range_rect, self.TRACK_RADIUS, self.TRACK_RADIUS)
            painter.fillPath(range_path, QBrush(self.COLOR_RANGE))

        # ── Handles ─────────────────────────────────────────────────
        for which in ("lower", "upper"):
            hr = self._handle_rect(which)
            handle_path = QPainterPath()
            handle_path.addRoundedRect(hr, self.HANDLE_RADIUS, self.HANDLE_RADIUS)

            if self._dragging == which:
                color = self.COLOR_HANDLE_DRAG
            elif self._hover_handle == which:
                color = self.COLOR_HANDLE_HOVER
            else:
                color = self.COLOR_HANDLE
            painter.fillPath(handle_path, QBrush(color))

    # ── Mouse interaction ──────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            hit = self._hit_handle(event.position().x())
            if hit:
                self._dragging = hit
                self._drag_anchor_value = self._lower if hit == "lower" else self._upper
                self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            new_val = self._x_to_value(event.position().x())
            if self._dragging == "lower":
                self.setLower(new_val)
            else:
                self.setUpper(new_val)
        else:
            # Update hover state
            prev_hover = self._hover_handle
            self._hover_handle = self._hit_handle(event.position().x())
            if prev_hover != self._hover_handle:
                self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = None
            self.update()
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if self._hover_handle is not None:
            self._hover_handle = None
            self.update()
        super().leaveEvent(event)
