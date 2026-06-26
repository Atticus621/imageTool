import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF

try:
    from .base import Shape
    from .registry import ShapeRegistry
    from ..utils import shapely_centroid, shapely_contains
except ImportError:
    from shapes.base import Shape
    from shapes.registry import ShapeRegistry
    from utils import shapely_centroid, shapely_contains


class PolygonShape(Shape):
    shape_type = "polygon"
    tool_label = "Polygon"
    draw_mode = "click_add"
    has_edges = False

    def __init__(self):
        super().__init__()
        self._vertices: list[QPointF] = []
        self._preview_point: QPointF | None = None
        self._has_rotation = True

    def _get_vertices_for_rotation(self) -> list:
        return self._vertices

    def _set_vertices_after_rotation(self, vertices: list):
        self._vertices = vertices

    def center(self) -> QPointF:
        return shapely_centroid(self._vertices)

    @property
    def vertices(self) -> list:
        return list(self._vertices)

    def add_vertex(self, point: QPointF):
        self._vertices.append(point)
        if len(self._vertices) == 3:
            self._init_axis_from_vertices(self._vertices)

    def set_preview_point(self, point: QPointF | None):
        self._preview_point = point

    @property
    def vertex_count(self) -> int:
        return len(self._vertices)

    def bounding_rect(self) -> QRectF:
        if not self._vertices:
            return QRectF()
        xs = [v.x() for v in self._vertices]
        ys = [v.y() for v in self._vertices]
        return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def contains_point(self, point: QPointF) -> bool:
        return shapely_contains(self._vertices, point)

    def control_points(self) -> list:
        return list(self._vertices)

    def edge_rects(self) -> dict:
        return {}

    def move(self, dx: float, dy: float):
        for i in range(len(self._vertices)):
            self._vertices[i] = QPointF(self._vertices[i].x() + dx, self._vertices[i].y() + dy)

    def resize_by_control(self, index: int, pos: QPointF):
        if 0 <= index < len(self._vertices):
            self._vertices[index] = QPointF(pos)

    def paint(self, painter: QPainter):
        if len(self._vertices) < 2:
            self._paint_vertices_only(painter)
            return
        c = self.center()
        if self.selected:
            painter.setPen(QPen(self.selected_border_color, 2.5))
            painter.setBrush(QBrush(self.selected_fill_color))
        else:
            painter.setPen(QPen(self.border_color, 2.0))
            painter.setBrush(QBrush(self.fill_color))
        painter.drawPolygon(QPolygonF(self._vertices))
        self.paint_center_cross(painter, c)
        self.paint_control_points(painter)
        self.paint_rotation_handle(painter, c)
        if self._preview_point and self._vertices:
            last = self._vertices[-1]
            painter.setPen(QPen(QColor(200, 200, 200, 150), 1, Qt.PenStyle.DashLine))
            painter.drawLine(last, self._preview_point)

    def _paint_vertices_only(self, painter: QPainter):
        for v in self._vertices:
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(v, 4, 4)

    def get_state_dict(self) -> dict:
        c = self.center()
        handle = self.rotation_handle_pos()
        return {
            "type": "polygon",
            "center": (round(c.x(), 2), round(c.y(), 2)),
            "vertex_count": len(self._vertices),
            "vertices": [(round(v.x(), 2), round(v.y(), 2)) for v in self._vertices],
            "rotation_handle": (round(handle.x(), 2), round(handle.y(), 2)),
        }

ShapeRegistry.register(PolygonShape)
