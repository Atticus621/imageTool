from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QWidget

from core.logger import logger
from systems.ruler.measure import RulerMeasure, MeasurementResult


@dataclass
class ScreenMeasurement:
    measurement: MeasurementResult
    screen_start: QPointF
    screen_end: QPointF


class RulerOverlay(QWidget):
    measurement_added = Signal(object)
    measurement_cleared = Signal()

    def __init__(self, parent=None, map_fn=None):
        """Args:
            parent: Parent QWidget.
            map_fn: Callable(overlay_x, overlay_y) -> (image_x, image_y) | None.
                    Injected by ImageViewerWidget, decoupling the overlay
                    from a specific parent widget's coordinate mapping.
        """
        super().__init__(parent)
        self._map_fn = map_fn
        self._measure = RulerMeasure()
        self._screen_measurements: list[ScreenMeasurement] = []
        self._drawing = False
        self._start_point: QPointF | None = None
        self._current_point: QPointF | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

    def set_visible(self, visible: bool):
        if visible:
            self.show()
            self.raise_()
        else:
            self.hide()

    def clear_measurements(self):
        self._screen_measurements.clear()
        self._drawing = False
        self._start_point = None
        self._current_point = None
        self.update()
        self.measurement_cleared.emit()

    def get_measurements(self) -> list[MeasurementResult]:
        return [sm.measurement for sm in self._screen_measurements]

    def _map_to_image(self, pos: QPointF) -> tuple[int, int] | None:
        """Map overlay-local coordinates to image pixel coordinates.

        Delegates to the injected map_fn (from ImageViewerWidget),
        which in turn delegates to DisplayInfo.map_to_image().
        """
        if self._map_fn:
            return self._map_fn(pos.x(), pos.y())
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            self._start_point = event.position()
            self._current_point = event.position()
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drawing:
            self._current_point = event.position()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            start = self._start_point
            end = event.position()
            if start and end:
                img_start = self._map_to_image(start)
                img_end = self._map_to_image(end)
                if img_start and img_end:
                    pixel_dist = self._measure.calculate_pixel_distance(img_start, img_end)
                    if pixel_dist > 2:
                        result = MeasurementResult(
                            start_point=img_start,
                            end_point=img_end,
                            pixel_distance=pixel_dist,
                        )
                        screen_sm = ScreenMeasurement(
                            measurement=result,
                            screen_start=QPointF(start),
                            screen_end=QPointF(end),
                        )
                        self._screen_measurements.append(screen_sm)
                        self.measurement_added.emit(result)
                        logger.info(f"Ruler: {pixel_dist:.1f}px "
                                    f"({img_start[0]},{img_start[1]}) -> ({img_end[0]},{img_end[1]})")
                else:
                    logger.warning("Ruler: could not map coordinates to image")
            self._start_point = None
            self._current_point = None
            self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for sm in self._screen_measurements:
            self._draw_measurement(painter, sm)

        if self._drawing and self._start_point and self._current_point:
            self._draw_preview(painter)

        painter.end()

    def _draw_measurement(self, painter: QPainter, sm: ScreenMeasurement):
        pen = QPen(QColor(0, 200, 255, 220), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawLine(sm.screen_start, sm.screen_end)

        self._draw_endpoint(painter, sm.screen_start)
        self._draw_endpoint(painter, sm.screen_end)

        m = sm.measurement
        text = f"{m.pixel_distance:.1f}px"
        if m.real_distance is not None:
            text += f" ({m.real_distance:.2f}{m.unit})"
        self._draw_distance_label(painter, sm.screen_start, sm.screen_end, text)

    def _draw_preview(self, painter: QPainter):
        pen = QPen(QColor(255, 200, 0, 200), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        painter.drawLine(self._start_point, self._current_point)

        self._draw_endpoint(painter, self._start_point)
        self._draw_endpoint(painter, self._current_point)

        img_start = self._map_to_image(self._start_point)
        img_end = self._map_to_image(self._current_point)
        if img_start and img_end:
            dist = self._measure.calculate_pixel_distance(img_start, img_end)
            text = f"{dist:.1f}px"
        else:
            text = "?"

        self._draw_distance_label(painter, self._start_point, self._current_point, text)

    def _draw_endpoint(self, painter: QPainter, point: QPointF):
        painter.setBrush(QColor(0, 200, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(point, 4, 4)

    def _draw_distance_label(self, painter: QPainter, p1: QPointF, p2: QPointF, text: str):
        mid = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)

        font = QFont("Consolas", 9)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        offset = 15
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        if abs(dx) > abs(dy):
            label_x = mid.x() - text_width / 2
            label_y = mid.y() - offset
        else:
            label_x = mid.x() + offset
            label_y = mid.y() - text_height / 2

        bg_rect = QRectF(label_x - 4, label_y - 2, text_width + 8, text_height + 4)
        painter.setBrush(QColor(0, 0, 0, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bg_rect, 4, 4)

        painter.setPen(QColor(0, 200, 255))
        painter.drawText(label_x, label_y + text_height - metrics.descent(), text)
