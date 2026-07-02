"""RulerOverlay — 图像测量尺子覆盖层。

覆盖在 QGraphicsView 的 viewport 上，允许用户在图像上绘制测量线。

使用 CoordinateMapper 进行坐标转换（消除分散的转换函数），
使用 EventGuard 管理事件拦截状态（消除手动状态管理）。
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QWidget

from core.logger import logger
from core.diagnostic.state_tracker import StateTracker
from systems.image_display.ruler.measure import MeasurementResult
from ui.widgets.coordinate_mapper import CoordinateMapper
from ui.widgets.event_guard import EventGuard


@dataclass
class ImageMeasurement:
    """存储在图像像素坐标中的测量结果。

    每次 paintEvent 时通过 CoordinateMapper 实时转换为屏幕坐标，
    所以尺子线条会跟随缩放/平移变化。
    """
    measurement: MeasurementResult
    img_start: tuple[int, int]
    img_end: tuple[int, int]


class RulerOverlay(QWidget):
    """图像测量尺子覆盖层。

    信号：
        measurement_added(object): 新增测量结果时发射
        measurement_cleared(): 清除所有测量时发射
    """

    measurement_added = Signal(object)
    measurement_cleared = Signal()

    def __init__(
        self,
        parent: QWidget,
        mapper: CoordinateMapper,
        ruler_system=None,
    ):
        """
        Args:
            parent: 父控件（通常是 QGraphicsView 的 viewport）
            mapper: 坐标转换器
            ruler_system: RulerSystem 实例，用于计算测量结果
        """
        super().__init__(parent)
        self._mapper = mapper
        self._guard = EventGuard()
        self._ruler_system = ruler_system
        self._image_measurements: list[ImageMeasurement] = []
        self._start_point: QPointF | None = None
        self._current_point: QPointF | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # Register for diagnostic state tracking
        StateTracker.register("ruler", self._get_state)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_visible(self, visible: bool) -> None:
        if visible:
            self.show()
            self.raise_()
        else:
            self.hide()

    def clear_measurements(self) -> None:
        self._image_measurements.clear()
        self._start_point = None
        self._current_point = None
        self.update()
        self.measurement_cleared.emit()

    def get_measurements(self) -> list[MeasurementResult]:
        return [m.measurement for m in self._image_measurements]

    def _get_state(self) -> dict:
        """Return current state for diagnostic tracking."""
        return {
            "measurements": len(self._image_measurements),
            "is_drawing": self._guard.is_drawing,
            "has_start": self._start_point is not None,
            "has_end": self._current_point is not None,
        }

    # ------------------------------------------------------------------
    # Event handling — delegated to EventGuard
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if self._guard.on_press(event):
            self._start_point = event.position()
            self._current_point = event.position()
            self.update()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._guard.on_move(event):
            if self._guard.is_drawing:
                self._current_point = event.position()
                self.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._guard.on_release(event):
            if not self._guard.is_drawing and self._start_point:
                self._create_measurement(event.position())
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._guard.on_leave()
        self._start_point = None
        self._current_point = None
        self.update()
        super().leaveEvent(event)

    # ------------------------------------------------------------------
    # Measurement creation
    # ------------------------------------------------------------------

    def _create_measurement(self, end_pos: QPointF) -> None:
        start = self._start_point
        end = end_pos
        if not start or not end:
            return

        img_start = self._mapper.viewport_to_image(start.x(), start.y())
        img_end = self._mapper.viewport_to_image(end.x(), end.y())
        if not img_start or not img_end:
            logger.warning("Ruler: could not map coordinates to image")
            return

        if self._ruler_system:
            result = self._ruler_system.create_measurement(img_start, img_end)
            pixel_dist = result.pixel_distance
        else:
            import math
            dx = img_end[0] - img_start[0]
            dy = img_end[1] - img_start[1]
            pixel_dist = math.sqrt(dx * dx + dy * dy)
            result = MeasurementResult(
                start_point=img_start,
                end_point=img_end,
                pixel_distance=pixel_dist,
            )

        if pixel_dist > 2:
            img_sm = ImageMeasurement(
                measurement=result,
                img_start=img_start,
                img_end=img_end,
            )
            self._image_measurements.append(img_sm)
            self.measurement_added.emit(result)
            logger.info(f"Ruler: {pixel_dist:.1f}px "
                        f"({img_start[0]},{img_start[1]}) -> ({img_end[0]},{img_end[1]})")

        self._start_point = None
        self._current_point = None
        self.update()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for img_m in self._image_measurements:
            self._draw_measurement(painter, img_m)

        if self._guard.is_drawing and self._start_point and self._current_point:
            self._draw_preview(painter)

        painter.end()

    def _draw_measurement(self, painter: QPainter, img_m: ImageMeasurement):
        screen_start = self._mapper.image_to_viewport(*img_m.img_start)
        screen_end = self._mapper.image_to_viewport(*img_m.img_end)

        pen = QPen(QColor(0, 200, 255, 220), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawLine(screen_start, screen_end)

        self._draw_endpoint(painter, screen_start)
        self._draw_endpoint(painter, screen_end)

        m = img_m.measurement
        text = f"{m.pixel_distance:.1f}px"
        if m.real_distance is not None:
            text += f" ({m.real_distance:.2f}{m.unit})"
        self._draw_distance_label(painter, screen_start, screen_end, text)

    def _draw_preview(self, painter: QPainter):
        pen = QPen(QColor(255, 200, 0, 200), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        painter.drawLine(self._start_point, self._current_point)
        self._draw_endpoint(painter, self._start_point)
        self._draw_endpoint(painter, self._current_point)

        img_start = self._mapper.viewport_to_image(self._start_point.x(), self._start_point.y())
        img_end = self._mapper.viewport_to_image(self._current_point.x(), self._current_point.y())
        if img_start and img_end and self._ruler_system:
            dist = self._ruler_system.calculate_pixel_distance(img_start, img_end)
            text = f"{dist:.1f}px"
        elif img_start and img_end:
            import math
            dx = img_end[0] - img_start[0]
            dy = img_end[1] - img_start[1]
            dist = math.sqrt(dx * dx + dy * dy)
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
