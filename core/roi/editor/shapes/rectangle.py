import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF

from core.roi.editor.shapes.base import Shape
from core.roi.editor.shapes.registry import ShapeRegistry
from core.roi.editor.utils import distance, rotate_point, shapely_centroid, shapely_contains


class RectangleShape(Shape):
    shape_type = "rect"
    tool_label = "Rectangle"
    draw_mode = "drag"
    has_edges = True

    def __init__(self, rect: QRectF):
        super().__init__()
        r = QRectF(rect).normalized()
        self._corners = [
            QPointF(r.left(), r.top()),
            QPointF(r.right(), r.top()),
            QPointF(r.right(), r.bottom()),
            QPointF(r.left(), r.bottom()),
        ]
        self._has_rotation = True
        self._init_axis_from_vertices(self._corners)

    def _get_vertices_for_rotation(self) -> list:
        return self._corners

    def _set_vertices_after_rotation(self, vertices: list):
        self._corners = vertices

    def center(self) -> QPointF:
        return shapely_centroid(self._corners)

    def bounding_rect(self) -> QRectF:
        xs = [v.x() for v in self._corners]
        ys = [v.y() for v in self._corners]
        return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def contains_point(self, point: QPointF) -> bool:
        return shapely_contains(self._corners, point)

    def control_points(self) -> list:
        return list(self._corners)

    def edge_rects(self) -> dict:
        d = 8.0
        result = {}
        edge_names = ["top", "right", "bottom", "left"]
        for i in range(4):
            p1 = self._corners[i]
            p2 = self._corners[(i + 1) % 4]
            mx = (p1.x() + p2.x()) / 2.0
            my = (p1.y() + p2.y()) / 2.0
            length = distance(p1, p2)
            angle = math.degrees(math.atan2(p2.y() - p1.y(), p2.x() - p1.x()))
            result[edge_names[i]] = {
                "center": QPointF(mx, my),
                "length": length,
                "angle": angle,
                "half_width": d,
            }
        return result

    def find_hit_edge(self, point: QPointF) -> str | None:
        edges = self.edge_rects()
        for name in ["top", "right", "bottom", "left"]:
            edge = edges.get(name)
            if not edge:
                continue
            ec = edge["center"]
            half_len = edge["length"] / 2.0
            hw = edge["half_width"]
            angle = edge["angle"]
            p = rotate_point(point, ec, -angle)
            if abs(p.x() - ec.x()) <= half_len and abs(p.y() - ec.y()) <= hw:
                return name
        return None

    def move(self, dx: float, dy: float):
        for i in range(4):
            self._corners[i] = QPointF(self._corners[i].x() + dx, self._corners[i].y() + dy)

    def resize_by_control(self, index: int, pos: QPointF):
        if 0 <= index < 4:
            opposite = (index + 2) % 4
            fixed = self._corners[opposite]
            dx = pos.x() - fixed.x()
            dy = pos.y() - fixed.y()
            half_w = max(abs(dx), 5)
            half_h = max(abs(dy), 5)
            sign_x = 1 if dx >= 0 else -1
            sign_y = 1 if dy >= 0 else -1
            self._corners = [
                QPointF(fixed.x(), fixed.y()),
                QPointF(fixed.x() + sign_x * half_w * 2, fixed.y()),
                QPointF(fixed.x() + sign_x * half_w * 2, fixed.y() + sign_y * half_h * 2),
                QPointF(fixed.x(), fixed.y() + sign_y * half_h * 2),
            ]

    def update_from_drag(self, start: QPointF, current: QPointF):
        rect = QRectF(start, current).normalized()
        self._corners = [
            QPointF(rect.left(), rect.top()),
            QPointF(rect.right(), rect.top()),
            QPointF(rect.right(), rect.bottom()),
            QPointF(rect.left(), rect.bottom()),
        ]

    def resize_edge(self, edge_name: str, delta_x: float, delta_y: float):
        edge_map = {"top": 0, "right": 1, "bottom": 2, "left": 3}
        idx = edge_map.get(edge_name)
        if idx is None:
            return
        p1 = self._corners[idx]
        p2 = self._corners[(idx + 1) % 4]
        edge_dx = p2.x() - p1.x()
        edge_dy = p2.y() - p1.y()
        edge_len = math.sqrt(edge_dx * edge_dx + edge_dy * edge_dy)
        if edge_len < 0.001:
            return
        nx, ny = -edge_dy / edge_len, edge_dx / edge_len
        proj = delta_x * nx + delta_y * ny
        if edge_name == "top":
            for i in [0, 1]:
                self._corners[i] = QPointF(self._corners[i].x() + nx * proj, self._corners[i].y() + ny * proj)
        elif edge_name == "bottom":
            for i in [2, 3]:
                self._corners[i] = QPointF(self._corners[i].x() + nx * proj, self._corners[i].y() + ny * proj)
        elif edge_name == "left":
            for i in [0, 3]:
                self._corners[i] = QPointF(self._corners[i].x() + nx * proj, self._corners[i].y() + ny * proj)
        elif edge_name == "right":
            for i in [1, 2]:
                self._corners[i] = QPointF(self._corners[i].x() + nx * proj, self._corners[i].y() + ny * proj)

    def paint(self, painter: QPainter):
        c = self.center()
        if self.selected:
            painter.setPen(QPen(self.selected_border_color, 2.5))
            painter.setBrush(QBrush(self.selected_fill_color))
        else:
            painter.setPen(QPen(self.border_color, 2.0))
            painter.setBrush(QBrush(self.fill_color))
        painter.drawPolygon(QPolygonF(self._corners))
        self.paint_center_cross(painter, c)
        self.paint_control_points(painter)
        self.paint_rotation_handle(painter, c)

    def get_state_dict(self) -> dict:
        c = self.center()
        handle = self.rotation_handle_pos()
        return {
            "type": "rectangle",
            "center": (round(c.x(), 2), round(c.y(), 2)),
            "corners": [(round(p.x(), 2), round(p.y(), 2)) for p in self._corners],
            "rotation_handle": (round(handle.x(), 2), round(handle.y(), 2)),
        }

ShapeRegistry.register(RectangleShape)
