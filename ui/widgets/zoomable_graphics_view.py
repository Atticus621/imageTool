"""ZoomableGraphicsView — QGraphicsView with explicit wheel-to-zoom handling.

QGraphicsView's default wheelEvent scrolls (not zooms), and when scrollbars
are hidden the event propagates to parent scroll areas.  This subclass
intercepts wheel events, applies a scale transform anchored under the cursor,
and accepts the event so it never escapes to a parent QScrollArea.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QGraphicsView


class ZoomableGraphicsView(QGraphicsView):
    """QGraphicsView that zooms on mouse wheel, pans on middle-button drag.

    Signals:
        zoom_changed(float): Emitted after each zoom with the new scale factor.
    """

    zoom_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_factor = 1.0
        self._zoom_step = 1.15
        self._min_zoom = 0.05
        self._max_zoom = 100.0
        self._panning = False
        self._pan_start = None

        # View behaviour
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)

    # ------------------------------------------------------------------
    # Wheel → zoom
    # ------------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Intercept wheel events and convert to zoom."""
        delta = event.angleDelta().y()
        if delta > 0:
            factor = self._zoom_step
        elif delta < 0:
            factor = 1.0 / self._zoom_step
        else:
            event.accept()
            return

        new_zoom = self._zoom_factor * factor
        if self._min_zoom <= new_zoom <= self._max_zoom:
            self.scale(factor, factor)
            self._zoom_factor = new_zoom
            self.zoom_changed.emit(self._zoom_factor)

        # Accept the event — prevents propagation to parent QScrollArea
        event.accept()

    # ------------------------------------------------------------------
    # Middle-button pan
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning and self._pan_start is not None:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def reset_zoom(self) -> None:
        """Reset transform to fitInView (the state after initial display)."""
        if self.scene() and self.scene().sceneRect().isValid():
            self.resetTransform()
            self.fitInView(
                self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
            )
            self._zoom_factor = self.transform().m11()
            self.zoom_changed.emit(self._zoom_factor)

    def get_zoom_factor(self) -> float:
        """Current scale factor (1.0 = original size)."""
        return self._zoom_factor
