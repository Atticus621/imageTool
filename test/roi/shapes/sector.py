import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QTransform

try:
    from .base import Shape
    from .registry import ShapeRegistry
    from ..utils import distance, rotate_point
except ImportError:
    from shapes.base import Shape
    from shapes.registry import ShapeRegistry
    from utils import distance, rotate_point


class SectorShape(Shape):
    shape_type = "sector"
    tool_label = "Sector"
    draw_mode = "drag_multi"
    has_edges = True

    def __init__(self, center: QPointF, radius: float, start_angle: float, end_angle: float):
        super().__init__()
        self._center = QPointF(center)
        self._radius = max(radius, 0.0)
        self._start_angle = start_angle
        self._end_angle = end_angle
        self._start_angle_raw = start_angle
        self._end_angle_raw = end_angle
        self._has_rotation = False
        self._axis_dir = QPointF(0, 1)

    def center(self) -> QPointF:
        return QPointF(self._center)

    @property
    def radius(self) -> float:
        return self._radius

    @property
    def start_angle(self) -> float:
        return self._start_angle

    @property
    def end_angle(self) -> float:
        return self._end_angle

    def bounding_rect(self) -> QRectF:
        return QRectF(self._center.x() - self._radius, self._center.y() - self._radius,
                      self._radius * 2, self._radius * 2)

    def contains_point(self, point: QPointF) -> bool:
        dx = point.x() - self._center.x()
        dy = point.y() - self._center.y()
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > self._radius:
            return False
        
        angle = math.degrees(math.atan2(-dy, dx))  # Qt coordinate system
        if angle < 0:
            angle += 360
        
        start = self._start_angle % 360
        end = self._end_angle % 360
        
        if start <= end:
            return start <= angle <= end
        else:
            return angle >= start or angle <= end

    def control_points(self) -> list:
        start_rad = math.radians(self._start_angle)
        end_rad = math.radians(self._end_angle)
        cx, cy, r = self._center.x(), self._center.y(), self._radius
        mid_angle = (self._start_angle + self._end_angle) / 2
        mid_rad = math.radians(mid_angle)
        return [
            QPointF(self._center),
            QPointF(cx + r * math.cos(mid_rad), cy + r * math.sin(mid_rad)),
            QPointF(cx + r * math.cos(start_rad), cy + r * math.sin(start_rad)),
            QPointF(cx + r * math.cos(end_rad), cy + r * math.sin(end_rad)),
        ]

    def edge_rects(self) -> dict:
        return {"circumference": self.bounding_rect().adjusted(-6, -6, 6, 6)}

    def edge_hit(self, point: QPointF) -> bool:
        dx = point.x() - self._center.x()
        dy = point.y() - self._center.y()
        dist = math.sqrt(dx * dx + dy * dy)
        return abs(dist - self._radius) <= 6.0

    def resize_edge(self, edge_name: str, pos: QPointF, drag_prev: QPointF):
        self._radius = max(distance(pos, self._center), 5.0)

    def is_valid(self) -> bool:
        return self._radius >= self.min_size()

    def validate(self) -> list:
        warnings = []
        if self._radius < 0:
            warnings.append(f"[WARN] Negative radius: {self._radius}")
        return warnings

    def move(self, dx: float, dy: float):
        self._center = QPointF(self._center.x() + dx, self._center.y() + dy)

    @staticmethod
    def _unwrap_angle(new_angle: float, prev_angle: float) -> float:
        """Adjust new_angle by multiples of 360° to be as close as possible to prev_angle.

        This prevents angle jumps when the control point crosses the atan2 discontinuity
        at ±180° (the leftward direction in screen coordinates).
        """
        diff = (new_angle - prev_angle) % 360.0
        if diff > 180.0:
            diff -= 360.0
        return prev_angle + diff

    def resize_by_control(self, index: int, pos: QPointF):
        if index == 0:  # Center
            self._center = QPointF(pos)
        elif index == 1:  # Radius
            self._radius = max(distance(pos, self._center), 5.0)
        elif index == 2:  # Start angle
            dx = pos.x() - self._center.x()
            dy = pos.y() - self._center.y()
            raw = math.degrees(math.atan2(dy, dx))
            raw = self._unwrap_angle(raw, self._start_angle_raw)
            self._start_angle = raw % 360
            self._start_angle_raw = raw
        elif index == 3:  # End angle
            dx = pos.x() - self._center.x()
            dy = pos.y() - self._center.y()
            raw = math.degrees(math.atan2(dy, dx))
            raw = self._unwrap_angle(raw, self._end_angle_raw)
            self._end_angle = raw % 360
            self._end_angle_raw = raw

    def update_from_drag(self, start: QPointF, current: QPointF):
        self._center = QPointF(start)
        self._radius = max(distance(start, current), 5.0)
        dx = current.x() - start.x()
        dy = current.y() - start.y()
        raw = math.degrees(math.atan2(-dy, dx))
        self._start_angle = raw % 360
        self._start_angle_raw = raw
        self._end_angle = (raw + 90) % 360
        self._end_angle_raw = raw + 90

    def on_click(self, pos: QPointF) -> bool:
        if self._drawing_step == 0:
            self._center = QPointF(pos)
            self._drawing_step = 1
            return False
        elif self._drawing_step == 1:
            dx = pos.x() - self._center.x()
            dy = pos.y() - self._center.y()
            self._radius = max(distance(pos, self._center), 5.0)
            raw = math.degrees(math.atan2(-dy, dx))
            raw = self._unwrap_angle(raw, self._start_angle_raw)
            self._start_angle = raw % 360
            self._start_angle_raw = raw
            self._drawing_step = 2
            return False
        elif self._drawing_step == 2:
            dx = pos.x() - self._center.x()
            dy = pos.y() - self._center.y()
            raw = math.degrees(math.atan2(-dy, dx))
            raw = self._unwrap_angle(raw, self._end_angle_raw)
            self._end_angle = raw % 360
            self._end_angle_raw = raw
            self._drawing_complete = True
            return True
        return True

    def on_move(self, pos: QPointF):
        if self._drawing_step == 1:
            dx = pos.x() - self._center.x()
            dy = pos.y() - self._center.y()
            self._radius = max(distance(pos, self._center), 5.0)
            raw = math.degrees(math.atan2(-dy, dx))
            raw = self._unwrap_angle(raw, self._start_angle_raw)
            self._start_angle = raw % 360
            self._start_angle_raw = raw
        elif self._drawing_step == 2:
            dx = pos.x() - self._center.x()
            dy = pos.y() - self._center.y()
            raw = math.degrees(math.atan2(-dy, dx))
            raw = self._unwrap_angle(raw, self._end_angle_raw)
            self._end_angle = raw % 360
            self._end_angle_raw = raw

    def paint_guide(self, painter: QPainter):
        if self._radius < 1:
            painter.setPen(QPen(QColor(255, 255, 255, 150), 1, Qt.PenStyle.DashLine))
            s = 10.0
            painter.drawLine(QPointF(self._center.x() - s, self._center.y()),
                           QPointF(self._center.x() + s, self._center.y()))
            painter.drawLine(QPointF(self._center.x(), self._center.y() - s),
                           QPointF(self._center.x(), self._center.y() + s))

    def _build_sector_path(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(self._center)
        
        start_rad = math.radians(self._start_angle)
        cx, cy, r = self._center.x(), self._center.y(), self._radius
        
        start_point = QPointF(cx + r * math.cos(start_rad),
                              cy - r * math.sin(start_rad))
        path.lineTo(start_point)
        
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        span = self._end_angle_raw - self._start_angle_raw
        
        path.arcTo(rect, self._start_angle, span)
        path.lineTo(self._center)
        path.closeSubpath()
        
        return path

    def paint(self, painter: QPainter):
        path = self._build_sector_path()
        if self.selected:
            painter.setPen(QPen(self.selected_border_color, 2.5))
            painter.setBrush(QBrush(self.selected_fill_color))
        else:
            painter.setPen(QPen(self.border_color, 2.0))
            painter.setBrush(QBrush(self.fill_color))
        painter.drawPath(path)
        self.paint_center_cross(painter, self._center)
        self.paint_control_points(painter)

    def get_state_dict(self) -> dict:
        return {
            "type": "sector",
            "center": (round(self._center.x(), 2), round(self._center.y(), 2)),
            "radius": round(self._radius, 2),
            "start_angle": round(self._start_angle, 2),
            "end_angle": round(self._end_angle, 2),
        }

ShapeRegistry.register(SectorShape)
