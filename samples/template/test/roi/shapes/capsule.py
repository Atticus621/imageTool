import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QPolygonF, QTransform

try:
    from .base import Shape
    from .registry import ShapeRegistry
    from ..utils import distance, rotate_point
except ImportError:
    from shapes.base import Shape
    from shapes.registry import ShapeRegistry
    from utils import distance, rotate_point


class CapsuleShape(Shape):
    shape_type = "capsule"
    tool_label = "Capsule"
    draw_mode = "drag"
    has_edges = True

    def __init__(self, p1: QPointF, p2: QPointF, radius: float = 0):
        super().__init__()
        self._p1 = QPointF(p1)
        self._p2 = QPointF(p2)
        self._radius = max(radius, 0.0)
        self._has_rotation = True
        self._axis_dir = QPointF(0, 1)

    def center(self) -> QPointF:
        return QPointF((self._p1.x() + self._p2.x()) / 2,
                       (self._p1.y() + self._p2.y()) / 2)

    def bounding_rect(self) -> QRectF:
        xs = [self._p1.x(), self._p2.x()]
        ys = [self._p1.y(), self._p2.y()]
        r = self._radius
        return QRectF(min(xs) - r, min(ys) - r,
                      max(xs) - min(xs) + r * 2, max(ys) - min(ys) + r * 2)

    def _dist_to_segment(self, point: QPointF) -> float:
        ax, ay = self._p1.x(), self._p1.y()
        bx, by = self._p2.x(), self._p2.y()
        px, py = point.x(), point.y()
        dx, dy = bx - ax, by - ay
        len_sq = dx * dx + dy * dy
        if len_sq < 0.001:
            return distance(point, self._p1)
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / len_sq))
        proj_x = ax + t * dx
        proj_y = ay + t * dy
        return distance(point, QPointF(proj_x, proj_y))

    def contains_point(self, point: QPointF) -> bool:
        return self._dist_to_segment(point) <= self._radius

    def control_points(self) -> list:
        mx = (self._p1.x() + self._p2.x()) / 2
        my = (self._p1.y() + self._p2.y()) / 2
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.001:
            return [self._p1, self._p2,
                    QPointF(mx, my - self._radius),
                    QPointF(mx, my + self._radius)]
        nx, ny = -dy / length, dx / length
        return [
            self._p1,
            self._p2,
            QPointF(mx + nx * self._radius, my + ny * self._radius),
            QPointF(mx - nx * self._radius, my - ny * self._radius),
        ]

    def edge_rects(self) -> dict:
        return {"circumference": self.bounding_rect().adjusted(-6, -6, 6, 6)}

    def edge_hit(self, point: QPointF) -> bool:
        return abs(self._dist_to_segment(point) - self._radius) <= 6.0

    def resize_edge(self, edge_name: str, pos: QPointF, drag_prev: QPointF):
        self._radius = max(self._dist_to_segment(pos), 5.0)

    def is_valid(self) -> bool:
        length = distance(self._p1, self._p2)
        return length >= self.min_size() and self._radius >= self.min_size()

    def validate(self) -> list:
        warnings = []
        if self._radius < 0:
            warnings.append(f"[WARN] Negative radius: {self._radius}")
        return warnings

    def move(self, dx: float, dy: float):
        self._p1 = QPointF(self._p1.x() + dx, self._p1.y() + dy)
        self._p2 = QPointF(self._p2.x() + dx, self._p2.y() + dy)

    def resize_by_control(self, index: int, pos: QPointF):
        if index == 0:
            self._p1 = QPointF(pos)
        elif index == 1:
            self._p2 = QPointF(pos)
        elif index in (2, 3):
            self._radius = max(self._dist_to_segment(pos), 5.0)
        self._update_axis()

    def _update_axis(self):
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0.001:
            self._axis_dir = QPointF(dx / length, dy / length)

    def rotate_by(self, delta_angle: float):
        if abs(delta_angle) < 0.001:
            return
        c = self.center()
        self._p1 = rotate_point(self._p1, c, delta_angle)
        self._p2 = rotate_point(self._p2, c, delta_angle)
        self._update_axis()
        if self._axis_dir is not None:
            rotated = rotate_point(self._axis_dir, QPointF(0, 0), delta_angle)
            length = math.sqrt(rotated.x() ** 2 + rotated.y() ** 2)
            if length > 0.001:
                self._axis_dir = QPointF(rotated.x() / length, rotated.y() / length)

    def update_from_drag(self, start: QPointF, current: QPointF):
        self._p1 = QPointF(start)
        self._p2 = QPointF(current)
        dx = current.x() - start.x()
        dy = current.y() - start.y()
        length = math.sqrt(dx * dx + dy * dy)
        self._radius = max(length * 0.3, 10.0)
        self._update_axis()

    def on_click(self, pos: QPointF) -> bool:
        self._p1 = QPointF(pos)
        self._p2 = QPointF(pos)
        self._drawing_step = 1
        return False

    def on_move(self, pos: QPointF):
        if self._drawing_step == 1:
            self._p2 = QPointF(pos)
            dx = pos.x() - self._p1.x()
            dy = pos.y() - self._p1.y()
            length = math.sqrt(dx * dx + dy * dy)
            self._radius = max(length * 0.3, 10.0)
            self._update_axis()

    def _build_path(self) -> QPainterPath:
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        length = math.sqrt(dx * dx + dy * dy)
        r = self._radius
        if length < 0.001:
            path = QPainterPath()
            path.addEllipse(self._p1, r, r)
            return path
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        mx, my = (self._p1.x() + self._p2.x()) / 2, (self._p1.y() + self._p2.y()) / 2
        w = length + 2 * r
        h = 2 * r
        path = QPainterPath()
        path.addRoundedRect(-w / 2, -h / 2, w, h, r, r)
        angle = math.degrees(math.atan2(dy, dx))
        t = QTransform()
        t.translate(mx, my)
        t.rotate(angle)
        return t.map(path)

    def paint(self, painter: QPainter):
        path = self._build_path()
        if self.selected:
            painter.setPen(QPen(self.selected_border_color, 2.5))
            painter.setBrush(QBrush(self.selected_fill_color))
        else:
            painter.setPen(QPen(self.border_color, 2.0))
            painter.setBrush(QBrush(self.fill_color))
        painter.drawPath(path)
        self.paint_center_cross(painter, self.center())
        self.paint_control_points(painter)
        self.paint_rotation_handle(painter, self.center())

    def get_state_dict(self) -> dict:
        c = self.center()
        return {
            "type": "capsule",
            "center": (round(c.x(), 2), round(c.y(), 2)),
            "p1": (round(self._p1.x(), 2), round(self._p1.y(), 2)),
            "p2": (round(self._p2.x(), 2), round(self._p2.y(), 2)),
            "radius": round(self._radius, 2),
        }

ShapeRegistry.register(CapsuleShape)
