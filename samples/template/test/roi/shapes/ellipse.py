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


class EllipseShape(Shape):
    shape_type = "ellipse"
    tool_label = "Ellipse"
    draw_mode = "drag"
    has_edges = True

    def __init__(self, center: QPointF, rx: float, ry: float):
        super().__init__()
        self._center = QPointF(center)
        self._rx = max(rx, 0.0)
        self._ry = max(ry, 0.0)
        self._rotation_deg = 0.0
        self._has_rotation = True
        self._axis_dir = QPointF(0, 1)

    def center(self) -> QPointF:
        return QPointF(self._center)

    @property
    def rx(self) -> float:
        return self._rx

    @property
    def ry(self) -> float:
        return self._ry

    def bounding_rect(self) -> QRectF:
        cos_a = abs(math.cos(math.radians(self._rotation_deg)))
        sin_a = abs(math.sin(math.radians(self._rotation_deg)))
        half_w = self._rx * cos_a + self._ry * sin_a
        half_h = self._rx * sin_a + self._ry * cos_a
        return QRectF(self._center.x() - half_w, self._center.y() - half_h,
                      half_w * 2, half_h * 2)

    def contains_point(self, point: QPointF) -> bool:
        lp = rotate_point(point, self._center, -self._rotation_deg)
        dx = lp.x() - self._center.x()
        dy = lp.y() - self._center.y()
        if self._rx < 0.001 or self._ry < 0.001:
            return False
        return (dx / self._rx) ** 2 + (dy / self._ry) ** 2 <= 1.0

    def control_points(self) -> list:
        pts = [
            QPointF(self._center.x(), self._center.y() - self._ry),
            QPointF(self._center.x() + self._rx, self._center.y()),
            QPointF(self._center.x(), self._center.y() + self._ry),
            QPointF(self._center.x() - self._rx, self._center.y()),
        ]
        return [rotate_point(p, self._center, self._rotation_deg) for p in pts]

    def edge_rects(self) -> dict:
        return {"circumference": self.bounding_rect().adjusted(-6, -6, 6, 6)}

    def edge_hit(self, point: QPointF) -> bool:
        lp = rotate_point(point, self._center, -self._rotation_deg)
        dx = lp.x() - self._center.x()
        dy = lp.y() - self._center.y()
        if self._rx < 0.001 or self._ry < 0.001:
            return False
        val = (dx / self._rx) ** 2 + (dy / self._ry) ** 2
        return abs(val - 1.0) <= 0.15

    def _get_vertices_for_rotation(self) -> list:
        return self.control_points()

    def _set_vertices_after_rotation(self, vertices: list):
        pass

    def rotate_by(self, delta_angle: float):
        self._rotation_deg += delta_angle
        self._rotation_deg %= 360.0
        if self._axis_dir is not None:
            rotated = rotate_point(self._axis_dir, QPointF(0, 0), delta_angle)
            length = math.sqrt(rotated.x() ** 2 + rotated.y() ** 2)
            if length > 0.001:
                self._axis_dir = QPointF(rotated.x() / length, rotated.y() / length)

    def rotation_handle_pos(self) -> QPointF:
        direction = QPointF(self._axis_dir.x() * self._handle_sign,
                            self._axis_dir.y() * self._handle_sign)
        offset = max(self._rotation_handle_offset, self._ry + self._rotation_handle_offset)
        return QPointF(self._center.x() + direction.x() * offset,
                       self._center.y() + direction.y() * offset)

    def resize_edge(self, edge_name: str, pos: QPointF, drag_prev: QPointF):
        old_r = math.sqrt(self._rx ** 2 + self._ry ** 2)
        new_r = distance(pos, self._center)
        if old_r > 0.001:
            scale = new_r / old_r
            self._rx = max(self._rx * scale, 5.0)
            self._ry = max(self._ry * scale, 5.0)

    def is_valid(self) -> bool:
        return self._rx >= self.min_size() and self._ry >= self.min_size()

    def validate(self) -> list:
        warnings = []
        if self._rx < 0 or self._ry < 0:
            warnings.append(f"[WARN] Negative radius: rx={self._rx}, ry={self._ry}")
        return warnings

    def move(self, dx: float, dy: float):
        self._center = QPointF(self._center.x() + dx, self._center.y() + dy)

    def resize_by_control(self, index: int, pos: QPointF):
        lp = rotate_point(pos, self._center, -self._rotation_deg)
        dx = abs(lp.x() - self._center.x())
        dy = abs(lp.y() - self._center.y())
        if index in (0, 2):
            self._ry = max(dy, 5.0)
        elif index in (1, 3):
            self._rx = max(dx, 5.0)

    def update_from_drag(self, start: QPointF, current: QPointF):
        self._center = QPointF(start)
        self._rx = max(abs(current.x() - start.x()), 5.0)
        self._ry = max(abs(current.y() - start.y()), 5.0)

    def on_click(self, pos: QPointF) -> bool:
        self._center = QPointF(pos)
        self._drawing_step = 1
        return False

    def on_move(self, pos: QPointF):
        if self._drawing_step == 1:
            self._rx = max(abs(pos.x() - self._center.x()), 0.0)
            self._ry = max(abs(pos.y() - self._center.y()), 0.0)

    def _build_ellipse_path(self) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(self._center, self._rx, self._ry)
        if abs(self._rotation_deg) > 0.01:
            t = QTransform()
            t.translate(self._center.x(), self._center.y())
            t.rotate(self._rotation_deg)
            t.translate(-self._center.x(), -self._center.y())
            path = t.map(path)
        return path

    def paint(self, painter: QPainter):
        path = self._build_ellipse_path()
        if self.selected:
            painter.setPen(QPen(self.selected_border_color, 2.5))
            painter.setBrush(QBrush(self.selected_fill_color))
        else:
            painter.setPen(QPen(self.border_color, 2.0))
            painter.setBrush(QBrush(self.fill_color))
        painter.drawPath(path)
        self.paint_center_cross(painter, self._center)
        self.paint_control_points(painter)
        self.paint_rotation_handle(painter, self._center)

    def get_state_dict(self) -> dict:
        return {
            "type": "ellipse",
            "center": (round(self._center.x(), 2), round(self._center.y(), 2)),
            "rx": round(self._rx, 2),
            "ry": round(self._ry, 2),
            "rotation": round(self._rotation_deg, 2),
        }

ShapeRegistry.register(EllipseShape)
