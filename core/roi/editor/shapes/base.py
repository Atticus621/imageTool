import math
from abc import ABC, abstractmethod
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from core.roi.editor.utils import distance, rotate_point, shapely_rotate_points, polar_angle_group_axis


class Shape(ABC):
    shape_type = "base"
    tool_label = ""
    draw_mode = "none"
    has_edges = False

    def __init__(self):
        self.selected = False
        self.fill_color = QColor(0, 120, 215, 60)
        self.border_color = QColor(0, 120, 215, 200)
        self.selected_border_color = QColor(255, 165, 0, 255)
        self.selected_fill_color = QColor(255, 165, 0, 80)
        self.center_cross_color = QColor(255, 0, 0, 255)
        self.control_point_radius = 5.0
        self.center_cross_size = 10.0
        self._has_rotation = False
        self._rotation_handle_offset = 30.0
        self._axis_dir: QPointF | None = None
        self._handle_sign = 1.0

    @abstractmethod
    def center(self) -> QPointF: ...

    @abstractmethod
    def bounding_rect(self) -> QRectF: ...

    @abstractmethod
    def contains_point(self, point: QPointF) -> bool: ...

    @abstractmethod
    def paint(self, painter: QPainter): ...

    @abstractmethod
    def control_points(self) -> list: ...

    @abstractmethod
    def edge_rects(self) -> dict: ...

    @abstractmethod
    def move(self, dx: float, dy: float): ...

    @abstractmethod
    def resize_by_control(self, index: int, pos: QPointF): ...

    def edge_hit(self, point: QPointF) -> bool:
        return False

    def find_hit_edge(self, point: QPointF) -> str | None:
        return None

    def update_from_drag(self, start: QPointF, current: QPointF):
        pass

    def add_vertex(self, point: QPointF):
        pass

    def set_preview_point(self, point):
        pass

    @property
    def vertex_count(self) -> int:
        return 0

    def _get_vertices_for_rotation(self) -> list:
        return []

    def _set_vertices_after_rotation(self, vertices: list):
        pass

    def rotate_by(self, delta_angle: float):
        if abs(delta_angle) < 0.001:
            return
        verts = self._get_vertices_for_rotation()
        if len(verts) < 2:
            return
        c = self.center()
        self._set_vertices_after_rotation(shapely_rotate_points(verts, c, delta_angle))
        if self._axis_dir is not None:
            rotated = rotate_point(self._axis_dir, QPointF(0, 0), delta_angle)
            length = math.sqrt(rotated.x() ** 2 + rotated.y() ** 2)
            if length > 0.001:
                self._axis_dir = QPointF(rotated.x() / length, rotated.y() / length)

    @abstractmethod
    def get_state_dict(self) -> dict: ...

    def _init_axis_from_vertices(self, vertices: list):
        if len(vertices) < 2:
            self._axis_dir = QPointF(0, 1)
            return
        a, b = polar_angle_group_axis(vertices)
        dx = b.x() - a.x()
        dy = b.y() - a.y()
        length = math.sqrt(dx * dx + dy * dy)
        self._axis_dir = QPointF(dx / length, dy / length) if length > 0.001 else QPointF(0, 1)

    def rotation_handle_pos(self) -> QPointF:
        c = self.center()
        verts = self._get_vertices_for_rotation()
        direction = QPointF(self._axis_dir.x() * self._handle_sign, self._axis_dir.y() * self._handle_sign)
        max_proj = max(((v.x() - c.x()) * direction.x() + (v.y() - c.y()) * direction.y()) for v in verts) if verts else 0
        offset = max(self._rotation_handle_offset, max_proj + self._rotation_handle_offset)
        return QPointF(c.x() + direction.x() * offset, c.y() + direction.y() * offset)

    def rotation_hit(self, point: QPointF) -> bool:
        return distance(point, self.rotation_handle_pos()) <= 8.0

    def paint_rotation_handle(self, painter: QPainter, center: QPointF):
        if not self._has_rotation or not self.selected:
            return
        handle = self.rotation_handle_pos()
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.PenStyle.DashLine))
        painter.drawLine(center, handle)
        painter.setPen(QPen(QColor(255, 165, 0), 2))
        painter.setBrush(QBrush(QColor(255, 165, 0)))
        painter.drawEllipse(handle, 6, 6)

    def paint_center_cross(self, painter: QPainter, center: QPointF):
        pen = QPen(self.center_cross_color, 2.0)
        painter.setPen(pen)
        s = self.center_cross_size
        painter.drawLine(QPointF(center.x() - s, center.y()),
                         QPointF(center.x() + s, center.y()))
        painter.drawLine(QPointF(center.x(), center.y() - s),
                         QPointF(center.x(), center.y() + s))

    def paint_control_points(self, painter: QPainter):
        if not self.selected:
            return
        for cp in self.control_points():
            painter.setPen(QPen(QColor(0, 0, 0), 1.5))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(cp, self.control_point_radius, self.control_point_radius)

    def paint_selection_border(self, painter: QPainter, draw_func):
        if self.selected:
            painter.setPen(QPen(self.selected_border_color, 2.5))
            painter.setBrush(QBrush(self.selected_fill_color))
        else:
            painter.setPen(QPen(self.border_color, 2.0))
            painter.setBrush(QBrush(self.fill_color))
        draw_func()
