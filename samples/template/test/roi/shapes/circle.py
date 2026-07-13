from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

try:
    from .base import Shape
    from .registry import ShapeRegistry
    from ..utils import distance
except ImportError:
    from shapes.base import Shape
    from shapes.registry import ShapeRegistry
    from utils import distance


class CircleShape(Shape):
    shape_type = "circle"
    tool_label = "Circle"
    draw_mode = "drag"
    has_edges = True

    def __init__(self, center: QPointF, radius: float):
        super().__init__()
        self._center = center
        self._radius = max(radius, 0.0)

    def center(self) -> QPointF:
        return QPointF(self._center)

    @property
    def radius(self) -> float:
        return self._radius

    def bounding_rect(self) -> QRectF:
        return QRectF(self._center.x() - self._radius,
                      self._center.y() - self._radius,
                      self._radius * 2, self._radius * 2)

    def contains_point(self, point: QPointF) -> bool:
        return distance(point, self._center) <= self._radius

    def control_points(self) -> list:
        r = self._radius
        c = self._center
        return [
            QPointF(c.x(), c.y() - r),
            QPointF(c.x() + r, c.y()),
            QPointF(c.x(), c.y() + r),
            QPointF(c.x() - r, c.y()),
        ]

    def edge_rects(self) -> dict:
        c = self._center
        r = self._radius
        d = 6.0
        return {
            "circumference": QRectF(c.x() - r - d, c.y() - r - d,
                                    (r + d) * 2, (r + d) * 2),
        }

    def edge_hit(self, point: QPointF) -> bool:
        dist = distance(point, self._center)
        return abs(dist - self._radius) <= 6.0

    def move(self, dx: float, dy: float):
        self._center = QPointF(self._center.x() + dx, self._center.y() + dy)

    def resize_by_control(self, index: int, pos: QPointF):
        self._radius = max(distance(pos, self._center), 5.0)

    def update_from_drag(self, start: QPointF, current: QPointF):
        self._center = QPointF(start)
        self._radius = max(distance(start, current), 5.0)

    def rotate_by(self, delta_angle: float):
        pass

    def paint(self, painter: QPainter):
        self.paint_selection_border(painter, lambda: painter.drawEllipse(self._center, self._radius, self._radius))
        self.paint_center_cross(painter, self._center)
        self.paint_control_points(painter)

    def get_state_dict(self) -> dict:
        return {
            "type": "circle",
            "center": (round(self._center.x(), 2), round(self._center.y(), 2)),
            "radius": round(self._radius, 2),
        }

ShapeRegistry.register(CircleShape)
